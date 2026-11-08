// GitHub Pages has no rewrites: serving index.html as 404.html makes deep links work.
import { copyFileSync } from 'node:fs';
copyFileSync('dist/index.html', 'dist/404.html');
