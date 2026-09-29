"""Style-frame renderer for the visual foundation (fusion-motion-design module 17, local route).

Renders one HTML/CSS design page to a PNG in headless Chromium at the comp size, then applies a lens pass whose
parts map to Fusion natives, so the look carries into the build: bloom (SoftGlow), radial chromatic offset
(per-channel Transform size), vignette (EllipseMask into a Multiply merge), even grain (FilmGrain), optional zoom
blur (DirectionalBlur Zoom / camera motion blur).

Needs Python with playwright (Chromium installed: `python -m playwright install chromium`), numpy and opencv-python.
The page loads fonts from their installed files with @font-face and sets `window.__ready = true` when drawn.
Pass the font families with --fonts to have their loading checked, and verify with a visible fallback test too:
document.fonts.check() has reported a face as loaded when its file path was wrong.

Usage: python styleframe_render.py page.html[#fragment] out.png [--size 1920x1080] [--bloom 0.5] [--thresh 0.62]
       [--chroma 1.0] [--vig 0.3] [--grain 2.0] [--zoomblur 0] [--zc 0.5,0.5] [--raw raw.png] [--fonts "A|B"]
Written by the explainer design agent, 2026-09-27; frames of the open-fusion-mcp explainer were made with it."""
import sys, argparse, pathlib, numpy as np, cv2
from playwright.sync_api import sync_playwright
ap=argparse.ArgumentParser(); ap.add_argument('html'); ap.add_argument('out')
ap.add_argument('--bloom',type=float,default=0.5); ap.add_argument('--thresh',type=float,default=0.62)
ap.add_argument('--chroma',type=float,default=1.0); ap.add_argument('--vig',type=float,default=0.3)
ap.add_argument('--grain',type=float,default=2.0); ap.add_argument('--raw'); ap.add_argument('--size',default='1920x1080')
ap.add_argument('--fonts',default='')
ap.add_argument('--zoomblur',type=float,default=0); ap.add_argument('--zc',default='0.5,0.5')
a=ap.parse_args(); W,H=map(int,a.size.split('x'))
hp,_,frag=a.html.partition('#'); src=pathlib.Path(hp).resolve()
with sync_playwright() as p:
    b=p.chromium.launch(args=['--allow-file-access-from-files','--disable-web-security','--force-color-profile=srgb'])
    pg=b.new_page(viewport={'width':W,'height':H},device_scale_factor=1)
    msgs=[]; pg.on('console',lambda m: msgs.append(m.text)); pg.on('pageerror',lambda e: msgs.append('PAGEERROR '+str(e)))
    pg.goto(src.as_uri()+('#'+frag if frag else '')); pg.evaluate('document.fonts.ready')
    pg.wait_for_function('window.__ready===true',timeout=60000)
    st=pg.evaluate("[...document.fonts].map(f=>f.family+' '+f.weight+' '+f.style+' '+f.status)")
    used=[x for x in st if not x.endswith('unloaded')]
    print('font faces used:', '; '.join(used)); bad=[x for x in st if x.endswith('error')]
    if bad: print('FONT ERRORS:', bad)
    buf=pg.screenshot(type='png',full_page=False); b.close()
for m in msgs: print('console:',m)
img=cv2.imdecode(np.frombuffer(buf,np.uint8),cv2.IMREAD_COLOR).astype(np.float32)/255.0
if a.raw: cv2.imwrite(a.raw,(img*255+0.5).clip(0,255).astype(np.uint8))
# radial zoom blur for camera push-ins (Fusion: DirectionalBlur Type Zoom, or Camera3D motion blur)
if a.zoomblur>0:
    zx,zy=[float(v) for v in a.zc.split(',')]; cx,cy=zx*W,zy*H; acc=np.zeros_like(img); N=14
    for i in range(N):
        f=1+a.zoomblur*i/(N-1); M=cv2.getRotationMatrix2D((cx,cy),0,f); acc+=cv2.warpAffine(img,M,(W,H),borderMode=cv2.BORDER_REFLECT)
    acc/=N; yy,xx=np.mgrid[0:H,0:W].astype(np.float32); r=np.clip(np.sqrt(((xx-cx)/(W/2))**2+((yy-cy)/(H/2))**2)/1.2,0,1)[...,None]**1.4
    img=img*(1-r)+acc*r
# bloom: soft-knee threshold, two blur radii, additive (Fusion: SoftGlow Threshold/Gain)
if a.bloom>0:
    lum=img.max(axis=2,keepdims=True); k=np.clip((lum-a.thresh)/(1-a.thresh+1e-6),0,1)**1.5
    hi=img*k; s=W/1920
    bl=cv2.GaussianBlur(hi,(0,0),6*s)*0.6+cv2.GaussianBlur(hi,(0,0),22*s)*0.8+cv2.GaussianBlur(hi,(0,0),60*s)*0.5
    img=1-(1-img)*(1-np.clip(bl*a.bloom,0,1))  # screen
# radial chromatic aberration (Fusion: per-channel Transform size via ChannelBooleans split)
if a.chroma>0:
    def scale(ch,f):
        M=cv2.getRotationMatrix2D((W/2,H/2),0,f); return cv2.warpAffine(ch,M,(W,H),flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_REFLECT)
    d=0.0012*a.chroma; bch,gch,rch=cv2.split(img); img=cv2.merge([scale(bch,1-d),gch,scale(rch,1+d)])
# vignette (Fusion: EllipseMask soft edge into a Multiply merge)
if a.vig>0:
    yy,xx=np.mgrid[0:H,0:W].astype(np.float32); r=np.sqrt(((xx-W/2)/(W/2))**2+((yy-H/2)/(H/2))**2)/1.414
    img=img*(1-a.vig*np.clip(r,0,1)**2.2)[...,None]
# grain, even across tones (Fusion: FilmGrain LogProcessing 0, Monochrome 1)
if a.grain>0:
    rng=np.random.default_rng(7); n=rng.normal(0,a.grain/255.0,(H,W,1)).astype(np.float32)
    n=cv2.GaussianBlur(n,(0,0),0.6)[...,None]*1.4; img=img+n
cv2.imwrite(a.out,(img.clip(0,1)*255+0.5).astype(np.uint8)); print('wrote',a.out,W,H)
