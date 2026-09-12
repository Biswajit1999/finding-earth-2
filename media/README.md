# LinkedIn release media

- `finding-earth-2-linkedin-30s.mp4`: exactly 30.00 seconds, 1350×1080 (5:4),
  H.264 High Profile, yuv420p, 30 fps, silent, fast-start MP4.
- `finding-earth-2-linkedin-poster.png`: first-frame cover image.
- `LINKEDIN_CAPTION.md`: ready-to-post caption with the live observatory, source,
  paper/data repository, and Beyond Earth 2.0 links.

The video moves through the home observatory, observed/intrinsic population,
selection function, Venus falsification, distance/contact calculator, and author
conclusion. It uses on-screen text because many social videos begin muted.

Regenerate the raw browser capture while the development server is on port 3111:

```bash
cd web
node scripts/capture-linkedin-video.cjs
```

The published MP4 trims initial browser warm-up and retimes the full capture to
30 seconds. `ffmpeg -i media/finding-earth-2-linkedin-30s.mp4` verifies the
dimensions, codec, pixel format, frame rate, and duration.
