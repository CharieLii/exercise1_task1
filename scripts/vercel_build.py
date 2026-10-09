"""Copy the canonical frontend into Vercel's static CDN directory."""

from pathlib import Path
import shutil

root = Path(__file__).resolve().parent.parent
destination = root / 'public'
destination.mkdir(exist_ok=True)
for name in ('index.html', 'favicon.ico'):
    shutil.copy2(root / 'src' / 'static' / name, destination / name)
print('Static frontend prepared for Vercel.')
