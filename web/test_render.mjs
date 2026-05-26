import puppeteer from 'puppeteer';
import { spawn } from 'child_process';

const server = spawn('npm', ['run', 'dev'], { cwd: '/Users/purrnansshlal/dev/codemap/web' });

server.stdout.on('data', async (data) => {
  const output = data.toString();
  const match = output.match(/http:\/\/localhost:(\d+)/);
  if (match) {
    const port = match[1];
    console.log(`Server started on port ${port}, running puppeteer...`);
    try {
      const browser = await puppeteer.launch();
      const page = await browser.newPage();
      page.on('console', msg => console.log('BROWSER LOG:', msg.text()));
      page.on('pageerror', error => console.log('BROWSER ERROR:', error.message));
      await page.goto(`http://localhost:${port}`, { waitUntil: 'networkidle0' });
      await browser.close();
    } catch (e) {
      console.log('PUP ERROR:', e);
    }
    server.kill();
    process.exit(0);
  }
});
