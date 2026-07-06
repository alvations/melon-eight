#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 alvations (Melon Lab)
"""Export the landing theme to shareable media, straight from the game's synth.

The landing music is generated live in the browser (`static/audio.js`). This
script drives that same code headlessly through an OfflineAudioContext, so the
exported files are exactly what a player hears, then packages them:

  - static/audio/landing.ogg  a small looping-ish OGG (used as an asset)
  - static/audio/landing.mp4  a 1080p still-card video for YouTube etc.

The card shows the landing screen's text and style ("8 / Somewhere you can't
quite leave. / Choose a way through.").

Run locally (not in the sandboxed web session):

    pip install playwright imageio-ffmpeg soundfile numpy
    playwright install chromium
    python scripts/export_landing_media.py                 # both files
    python scripts/export_landing_media.py --seconds 300   # longer video
    python scripts/export_landing_media.py --only mp4      # or: ogg

Nothing here needs the Flask server: audio.js is loaded directly.

NOTE: the arpeggio constants below mirror `_landing` in static/audio.js. If you
retune the landing theme there, mirror the change here (or vice versa).
"""

from __future__ import annotations

import argparse
import base64
import os
import sys

import numpy as np
import soundfile as sf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIO_JS = os.path.join(ROOT, "static", "audio.js")
OUT_DIR = os.path.join(ROOT, "static", "audio")
SR = 44100

# The landing card: the select screen's text and style, sized for 1080p.
CARD_HTML = """
<!doctype html><html><head><meta charset=utf-8><style>
 html,body{margin:0;height:100%}
 body{width:1920px;height:1080px;display:flex;align-items:center;justify-content:center;
   background:radial-gradient(120% 90% at 50% -12%, hsl(212 8% 10%), #0b0c0e 72%);
   color:#d7d7d2;font-family:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,'DejaVu Serif',serif;}
 .wrap{text-align:center}
 .title{font-size:10rem;font-weight:300;letter-spacing:.18em;margin:0 0 2.4rem;color:#e6e6e1}
 .lead{color:#7d8088;font-size:2rem;line-height:2.4}
</style></head><body>
 <div class=wrap>
   <div class=title>8</div>
   <div class=lead>Somewhere you can't quite leave.<br>Choose a way through.</div>
 </div>
</body></html>
"""

# Renders the landing theme to a mono WAV blob and downloads it. The synthesis
# reuses audio.js helpers (window.ambience.constructor); only the scheduling is
# unrolled here (audio.js schedules with setTimeout, which offline render skips).
AUDIO_JS_RENDER = """
async ([SR, dur, fadeIn, fadeOut]) => {
  const wr = (dv,o,s)=>{ for(let i=0;i<s.length;i++) dv.setUint8(o+i, s.charCodeAt(i)); };
  const Amb = window.ambience.constructor; const amb = new Amb();
  const off = new OfflineAudioContext(1, Math.floor(SR*dur), SR);
  amb.ctx = off;
  const bus = off.createGain(); bus.gain.value=1; bus.connect(off.destination);
  const verb = amb._reverb(3.2,2.6); const verbG = amb._gain(0.5); verb.connect(verbG).connect(bus);
  const voice = amb._gain(0.042); voice.connect(bus);           // mirrors _landing
  const padG = amb._gain(0.0126); padG.connect(bus);
  const pad = amb._noise(4); pad.connect(amb._filter('lowpass',240,0.5)).connect(padG); pad.start(0);
  const chords=[[57,60,64],[53,57,60,64],[48,52,55,60],[55,59,62]];  // vi-IV-I-V
  const step=0.22, ring=0.95, perChord=12;
  let idx=0, t=0.05;
  while (t < dur-0.02){
    const c=chords[Math.floor(idx/perChord)%chords.length];
    const tones=c.concat(c.map(m=>m+12));
    const seq=tones.concat(tones.slice(1,-1).reverse());
    amb._pluck(voice, verb, amb._mtof(seq[idx%seq.length]), t, ring);
    t+=step; idx++;
  }
  const buf = await off.startRendering();
  const d = buf.getChannelData(0);
  let peak=0; for(let i=0;i<d.length;i++){const a=Math.abs(d[i]); if(a>peak)peak=a;}
  const g = peak? 0.89/peak : 1;   // normalise for standalone playback
  const N=d.length, fi=Math.floor(SR*fadeIn), fo=Math.floor(SR*fadeOut);
  const ab=new ArrayBuffer(44+N*2); const dv=new DataView(ab);
  wr(dv,0,'RIFF'); dv.setUint32(4,36+N*2,true); wr(dv,8,'WAVE'); wr(dv,12,'fmt ');
  dv.setUint32(16,16,true); dv.setUint16(20,1,true); dv.setUint16(22,1,true);
  dv.setUint32(24,SR,true); dv.setUint32(28,SR*2,true); dv.setUint16(32,2,true); dv.setUint16(34,16,true);
  wr(dv,36,'data'); dv.setUint32(40,N*2,true);
  let o=44;
  for(let i=0;i<N;i++){ let s=d[i]*g; if(i<fi)s*=i/fi; if(i>=N-fo)s*=(N-i)/fo;
    s=Math.max(-1,Math.min(1,s)); dv.setInt16(o,s*32767,true); o+=2; }
  const blob=new Blob([ab],{type:'audio/wav'}); const url=URL.createObjectURL(blob);
  const a=document.createElement('a'); a.href=url; a.download='landing.wav';
  document.body.appendChild(a); a.click();
  return N;
}
"""


def _launch(p):
    """Launch Chromium, tolerating this repo's sandbox layout or a normal install."""
    import glob
    try:
        return p.chromium.launch()
    except Exception:
        hits = sorted(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome"))
        if not hits:
            raise
        return p.chromium.launch(executable_path=hits[-1])


def render_wav(page, seconds, fade_in, fade_out, dest):
    page.set_content("<!doctype html><html><body></body></html>")
    page.add_script_tag(path=AUDIO_JS)
    with page.expect_download(timeout=120000) as di:
        page.evaluate(AUDIO_JS_RENDER, [SR, seconds, fade_in, fade_out])
    di.value.save_as(dest)
    return dest


def render_card(page, dest):
    page.set_content(CARD_HTML)
    page.wait_for_timeout(300)
    page.screenshot(path=dest)
    return dest


def wav_to_ogg(wav_path, ogg_path):
    data, sr = sf.read(wav_path)
    sf.write(ogg_path, data, sr, format="OGG", subtype="VORBIS")


def mux_video(card_png, wav_path, out_mp4, fps=24):
    import subprocess
    import imageio_ffmpeg

    ff = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run(
        [ff, "-y", "-hide_banner", "-loglevel", "error",
         "-loop", "1", "-framerate", str(fps), "-i", card_png,
         "-i", wav_path,
         "-c:v", "libx264", "-tune", "stillimage", "-preset", "medium",
         "-pix_fmt", "yuv420p", "-r", str(fps),
         "-c:a", "aac", "-b:a", "192k", "-ar", str(SR),
         "-shortest", "-movflags", "+faststart", out_mp4],
        check=True,
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seconds", type=float, default=120, help="video length (s)")
    ap.add_argument("--ogg-seconds", type=float, default=42.24, help="ogg length (s)")
    ap.add_argument("--only", choices=["ogg", "mp4"], help="produce just one")
    ap.add_argument("--out-dir", default=OUT_DIR)
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    tmp = os.path.join(args.out_dir, "_landing_tmp.wav")
    card = os.path.join(args.out_dir, "_landing_card.png")

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = _launch(p)
        ctx = browser.new_context(
            viewport={"width": 1920, "height": 1080}, accept_downloads=True
        )
        page = ctx.new_page()

        if args.only != "mp4":
            render_wav(page, args.ogg_seconds, 0.4, 0.6, tmp)
            wav_to_ogg(tmp, os.path.join(args.out_dir, "landing.ogg"))
            print("wrote landing.ogg")

        if args.only != "ogg":
            render_wav(page, args.seconds, 0.6, 1.8, tmp)
            render_card(page, card)
            mux_video(card, tmp, os.path.join(args.out_dir, "landing.mp4"))
            print("wrote landing.mp4")

        browser.close()

    for f in (tmp, card):
        if os.path.exists(f):
            os.remove(f)


if __name__ == "__main__":
    sys.exit(main())
