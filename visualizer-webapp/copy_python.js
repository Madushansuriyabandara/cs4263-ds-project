import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const srcDir = path.join(__dirname, '..', 'src');
const destDir = path.join(__dirname, 'public', 'python_src');

// Remove existing destDir to clear out deleted files
if (fs.existsSync(destDir)) {
  fs.rmSync(destDir, { recursive: true, force: true });
}

fs.mkdirSync(destDir, { recursive: true });

// Read all files in srcDir
const files = fs.readdirSync(srcDir);
let count = 0;

for (const file of files) {
  if (file.endsWith('.py')) {
    fs.copyFileSync(path.join(srcDir, file), path.join(destDir, file));
    count++;
  }
}

console.log(`[copy_python.js] Copied ${count} Python source files from root src/ to public/python_src/`);
