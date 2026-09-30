"""Browser smoke check against an isolated database, never the farmer database."""
import json
import sys
import tempfile
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import create_app
from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server


def main():
    artifacts = Path('artifacts')
    artifacts.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='agriwise-browser-') as temp:
        app = create_app({'TESTING': True, 'CSRF_ENABLED': True, 'SECRET_KEY': 'browser-test', 'DATABASE': str(Path(temp) / 'browser.db')})
        server = make_server('127.0.0.1', 5056, app)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        errors, results = [], []
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(channel='msedge', headless=True)
                page = browser.new_page(viewport={'width': 1366, 'height': 900})
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto('http://127.0.0.1:5056/register')
                page.fill('[name=name]', 'Browser Farmer')
                page.fill('[name=email]', 'browser@example.com')
                page.fill('[name=password]', 'secret123')
                page.locator('button[type=submit]').click()
                page.wait_for_url('**/farm/setup')
                page.locator('#btnManualLocation').click()
                page.fill('[name=latitude]', '18.5')
                page.fill('[name=longitude]', '73.8')
                page.fill('[name=location_name]', 'Manual test location')
                page.fill('[name=farm_name]', 'Browser Farm')
                page.check('[name=no_soil_test]')
                page.locator('button[type=submit]').click()
                page.wait_for_url('**/dashboard')
                for path in ['/dashboard', '/weather', '/daily-plan', '/seven-day-plan', '/crop-recommendation', '/activities', '/resources', '/market', '/expenses', '/report', '/ml-analytics']:
                    response = page.goto('http://127.0.0.1:5056' + path)
                    page.wait_for_timeout(250)
                    results.append({'path': path, 'status': response.status})
                page.set_viewport_size({'width': 390, 'height': 844})
                page.goto('http://127.0.0.1:5056/dashboard')
                page.screenshot(path=str(artifacts / 'mobile_dashboard.png'), full_page=True)
                browser.close()
        finally:
            server.shutdown()
        report = {'pages': results, 'javascript_errors': errors}
        (artifacts / 'browser_results.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(json.dumps(report))
        if errors or any(item['status'] != 200 for item in results):
            raise SystemExit(1)


if __name__ == '__main__':
    main()
