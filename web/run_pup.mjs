import puppeteer from 'puppeteer';
import { spawn } from 'child_process';

const server = spawn('npm', ['run', 'dev'], { cwd: '/Users/purrnansshlal/dev/codemap/web' });

setTimeout(async () => {
  try {
    const browser = await puppeteer.launch();
    const page = await browser.newPage();
    
    page.on('console', msg => console.log('BROWSER LOG:', msg.text()));
    page.on('pageerror', error => console.log('BROWSER ERROR:', error.message));
    
    console.log('Navigating...');
    await page.goto('http://localhost:5173', { waitUntil: 'networkidle0' });
    console.log('Done.');
    
    await browser.close();
  } catch (e) {
    console.log('PUPPETEER ERROR:', e);
  } finally {
    server.kill();
    process.exit(0);
  }
}, 3000);
