"""Run the connector's Lua chunks offline in LuaJIT (the libluajit shipped inside DaVinci Resolve, loaded with ctypes; no Resolve
process is involved) against a mock Fusion comp written in Lua. The mock counts every API call, so a test can show that a chunk's
work grows with the pasted set, not with the comp. It models the API as the connector uses it (FindTool, GetToolList, GetAttrs,
Paste of a bmd.readfile table with Fusion's _1 collision rename and dropped external SourceOps, ConnectInput, Delete, FlowView
positions, enabled regions); it proves chunk logic, not Fusion's behaviour. Tests skip when the library is absent."""
import ctypes
import os

LIB = os.environ.get("FUSION_MCP_LUAJIT", "/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/libluajit-5.1.2.dylib")

MOCK = r"""
calls = {}
local function tick(k) calls[k] = (calls[k] or 0) + 1 end
local Tools = {}
local ToolM, InM, OutM = {}, {}, {}
local function main_out(reg)
  if string.sub(reg, -4) == "Mask" then return "Mask" end
  if reg == "BezierSpline" or reg == "XYPath" or reg == "PolyPath" then return "Value" end
  if reg == "StyledTextFollower" then return "StyledText" end
  return "Output"
end
local function out_of(t, id) return setmetatable({_t = t, _id = id or main_out(t._reg)}, OutM) end
local function input_of(t, id) return setmetatable({_t = t, _id = id}, InM) end
local function new_tool(name, reg)
  local t = setmetatable({_name = name, _reg = reg, _ins = {}, _data = {}, _attrs = {}, _pos = {0, 0}}, ToolM)
  Tools[name] = t
  return t
end
MockNewTool = new_tool
local methods = {}
function methods.GetAttrs(t)
  tick("GetAttrs")
  local a = {TOOLS_Name = t._name, TOOLS_RegID = t._reg}
  for k, v in pairs(t._attrs) do a[k] = v end
  return a
end
function methods.SetAttrs(t, a)
  tick("SetAttrs")
  for k, v in pairs(a) do
    if k == "TOOLS_Name" then Tools[t._name] = nil t._name = v Tools[v] = t else t._attrs[k] = v end
  end
end
function methods.ResetEnabledRegion(t) tick("ResetEnabledRegion") t._attrs.TOOLNT_EnabledRegion_Start = nil t._attrs.TOOLNT_EnabledRegion_End = nil end
function methods.Delete(t)
  tick("Delete")
  if Tools[t._name] ~= t then return false end
  Tools[t._name] = nil
  t._dead = true
  return true
end
function methods.GetInputList(t)
  tick("GetInputList")
  local l, i = {}, 0
  for id, _ in pairs(t._ins) do i = i + 1 l[i] = input_of(t, id) end
  return l
end
function methods.GetOutputList(t) tick("GetOutputList") return {out_of(t)} end
function methods.FindMainOutput(t, i) tick("FindMainOutput") return out_of(t) end
function methods.ConnectInput(t, id, src)
  tick("ConnectInput")
  local e = t._ins[id] or {}
  t._ins[id] = e
  if src == nil then e.src = nil return true end
  if getmetatable(src) == OutM then e.src = src else e.src = out_of(src) end
  e.value = nil
  return true
end
function methods.SetInput(t, id, v) tick("SetInput") t._ins[id] = {value = v} end
function methods.GetInput(t, id) tick("GetInput") return (t._ins[id] or {}).value end
function methods.GetData(t, k) return t._data[k] end
function methods.SetData(t, k, v) t._data[k] = v end
ToolM.__index = function(t, k)
  if methods[k] then return methods[k] end
  if type(k) == "string" and string.match(k, "^[A-Z][%w%.]*$") then tick("InputIndex") return input_of(t, k) end
  return nil
end
local imethods = {}
function imethods.GetAttrs(i) tick("InputGetAttrs") return {INPS_ID = i._id, INPS_Name = i._id} end
function imethods.GetConnectedOutput(i)
  tick("GetConnectedOutput")
  local e = i._t._ins[i._id]
  if e and e.src and not e.src._t._dead then return e.src end
  return nil
end
function imethods.GetTool(i) return i._t end
function imethods.SetExpression(i, e) tick("SetExpression") local x = i._t._ins[i._id] or {} i._t._ins[i._id] = x x.expr = e end
function imethods.ConnectTo(i, o) tick("ConnectTo") local e = i._t._ins[i._id] or {} i._t._ins[i._id] = e e.src = o return true end
InM.__index = imethods
local omethods = {}
function omethods.GetTool(o) return o._t end
function omethods.GetAttrs(o) tick("OutputGetAttrs") return {OUTS_ID = o._id} end
function omethods.GetConnectedInputs(o)
  tick("GetConnectedInputs")
  local l, i = {}, 0
  for _, t in pairs(Tools) do
    for id, e in pairs(t._ins) do
      if e.src and e.src._t == o._t and e.src._id == o._id then i = i + 1 l[i] = input_of(t, id) end
    end
  end
  return l
end
OutM.__index = omethods

-- .setting / spec files: Lua table text with constructors (Background { ... }, Input { ... }, ordered() { ... })
local env = setmetatable({ordered = function() return function(t) return t end end},
  {__index = function(_, k) return function(t) if type(t) == "table" then t.__ctor = k end return t end end})
local data = {}
MockFiles = data
bmd = {}
function bmd.readfile(p)
  tick("readfile")
  local s = data[p]
  if s == nil then local f = io.open(p, "r") if not f then return nil end s = f:read("*a") f:close() end
  local fn = loadstring("return " .. s)
  if not fn then return nil end
  setfenv(fn, env)
  local ok, v = pcall(fn)
  if ok then return v end
  return nil
end

local flow = {}
function flow.GetPos(self, t) tick("GetPos") return t._pos[1], t._pos[2] end
function flow.SetPos(self, t, x, y) tick("SetPos") t._pos = {x, y} end
function flow.QueueSetPos(self, t, x, y) tick("QueueSetPos") t._pos = {x, y} end
function flow.FlushSetPosQueue(self) tick("FlushSetPosQueue") end
comp = {CurrentFrame = {FlowView = flow}, _data = {}}
function comp:FindTool(n) tick("FindTool") return Tools[n] end
function comp:GetToolList(sel)
  tick("GetToolList")
  local l, i = {}, 0
  for _, t in pairs(Tools) do i = i + 1 l[i] = t end
  return l
end
function comp:Lock() tick("Lock") end
function comp:Unlock() tick("Unlock") end
function comp:SetActiveTool(t) tick("SetActiveTool") end
function comp:SetData(k, v) self._data[k] = v end
function comp:GetData(k) return self._data[k] end
function comp:Paste(s)
  tick("Paste")
  local tools = s.Tools or {}
  local map, made = {}, {}
  for name, def in pairs(tools) do
    local n, i = name, 0
    while Tools[n] do i = i + 1 n = name .. "_" .. i end
    map[name] = n
    local t = new_tool(n, def.__ctor or "?")
    made[#made + 1] = {t, def}
    local vi = def.ViewInfo
    if vi and vi.Pos then t._pos = {vi.Pos[1] / 110 - 0.5, vi.Pos[2] / 33 - 0.5} end
    if def.CustomData then for k, v in pairs(def.CustomData) do t._data[k] = v end end
  end
  for _, m in ipairs(made) do
    local t, def = m[1], m[2]
    for id, inp in pairs(def.Inputs or {}) do
      if type(inp) == "table" and inp.SourceOp then
        if map[inp.SourceOp] then t._ins[id] = {src = out_of(Tools[map[inp.SourceOp]], inp.Source)} end  -- external SourceOps drop
      elseif type(inp) == "table" then
        t._ins[id] = {value = inp.Value}
      end
    end
  end
  return true
end
function MockTool(name) return Tools[name] end
function MockCount() local n = 0 for _ in pairs(Tools) do n = n + 1 end return n end
"""


def available():
    return os.path.exists(LIB)


class Lua:
    """One Lua state with the mock loaded. run(code) executes Lua and returns its first result as a string."""

    def __init__(self):
        L = ctypes.CDLL(LIB)
        L.luaL_newstate.restype = ctypes.c_void_p
        L.luaL_openlibs.argtypes = [ctypes.c_void_p]
        L.luaL_loadstring.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        L.lua_pcall.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int]
        L.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_size_t)]
        L.lua_tolstring.restype = ctypes.c_char_p
        L.lua_settop.argtypes = [ctypes.c_void_p, ctypes.c_int]
        L.lua_close.argtypes = [ctypes.c_void_p]
        self.L, self.s = L, L.luaL_newstate()
        L.luaL_openlibs(self.s)
        self.run(MOCK)

    def run(self, code):
        L, s = self.L, self.s
        if L.luaL_loadstring(s, code.encode("utf-8")) != 0:
            msg = L.lua_tolstring(s, -1, None)
            L.lua_settop(s, 0)
            raise SyntaxError((msg or b"?").decode())
        if L.lua_pcall(s, 0, 1, 0) != 0:
            msg = L.lua_tolstring(s, -1, None)
            L.lua_settop(s, 0)
            raise RuntimeError((msg or b"?").decode())
        v = L.lua_tolstring(s, -1, None)
        L.lua_settop(s, 0)
        return v.decode("utf-8") if v is not None else None

    def close(self):
        self.L.lua_close(self.s)

    # ---- helpers
    def fill(self, n, reg="Background", prefix="Fill"):
        self.run("for i = 0, %d do MockNewTool('%s' .. i, '%s') end" % (n - 1, prefix, reg))

    def calls(self):
        out = self.run("local t = {} for k, v in pairs(calls) do t[#t + 1] = k .. '=' .. v end return table.concat(t, ',')")
        return {k: int(v) for k, v in (x.split("=") for x in out.split(",") if x)}

    def reset_calls(self):
        self.run("calls = {}")

    def tools(self):
        return sorted(x for x in self.run("local t = {} for _, x in pairs(comp:GetToolList(false)) do t[#t + 1] = x._name end "
                                          "calls.GetToolList = calls.GetToolList - 1 return table.concat(t, ',')").split(",") if x)

    def execute(self, wrapped, key):
        """What comp:Execute does with the Ctx.lua wrapper: run it, then read the status the wrapper stored."""
        self.run(wrapped)
        return self.run("return comp:GetData(%r)" % key)
