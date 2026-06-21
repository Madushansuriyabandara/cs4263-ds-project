import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// 1. Sync Python Sources
const pySrcDir = path.join(__dirname, '..', 'src');
const pyDestDir = path.join(__dirname, 'public', 'python_src');

if (fs.existsSync(pyDestDir)) {
  fs.rmSync(pyDestDir, { recursive: true, force: true });
}
fs.mkdirSync(pyDestDir, { recursive: true });

const pyFiles = fs.readdirSync(pySrcDir);
let pyCount = 0;
for (const file of pyFiles) {
  if (file.endsWith('.py')) {
    fs.copyFileSync(path.join(pySrcDir, file), path.join(pyDestDir, file));
    pyCount++;
  }
}
console.log(`[sync_assets.js] Copied ${pyCount} Python source files from root src/ to public/python_src/`);

// 2. Sync Test Inputs
const inSrcDir = path.join(__dirname, '..', 'inputs');
const inDestDir = path.join(__dirname, 'public', 'data');

if (!fs.existsSync(inDestDir)) {
  fs.mkdirSync(inDestDir, { recursive: true });
}

const inFiles = fs.readdirSync(inSrcDir);
const inputList = [];
let inCount = 0;

for (const file of inFiles) {
  if (file.endsWith('.txt')) {
    // We prefix 'ext_' to dynamically loaded inputs if we want, or just keep their exact name
    const srcPath = path.join(inSrcDir, file);
    const destPath = path.join(inDestDir, file);
    fs.copyFileSync(srcPath, destPath);
    inputList.push(file.replace('.txt', ''));
    inCount++;
  }
}

// Write the list of input datasets to a JSON file
const listDestPath = path.join(inDestDir, 'input_list.json');
fs.writeFileSync(listDestPath, JSON.stringify(inputList, null, 2));

console.log(`[sync_assets.js] Copied ${inCount} input text files from root inputs/ to public/data/`);
console.log(`[sync_assets.js] Generated input_list.json with ${inputList.length} entries`);
