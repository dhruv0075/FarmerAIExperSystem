"""Browser smoke check against an isolated database, never the farmer database."""
import json
import io
import sys
import tempfile
import threading
from pathlib import Path
from PIL import Image

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
        errors, results, failed_requests, bad_responses = [], [], [], []
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(channel='msedge', headless=True)
                page = browser.new_page(viewport={'width': 1366, 'height': 900})
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.on('requestfailed', lambda request: failed_requests.append({'url': request.url, 'failure': request.failure}))
                page.on('response', lambda response: bad_responses.append({'url': response.url, 'status': response.status}) if response.status >= 400 else None)
                page.on('dialog', lambda dialog: dialog.accept())
                home_response = page.goto('http://127.0.0.1:5056/', wait_until='domcontentloaded')
                assert home_response.status == 200
                page.wait_for_function("document.querySelector('[data-farm-scene=field]').dataset.sceneState !== 'loading'", timeout=15000)
                home_scene = page.evaluate("""() => {
                    const scene = document.querySelector('[data-farm-scene=field]');
                    const canvas = scene.querySelector('canvas');
                    const gl = canvas.getContext('webgl2');
                    return {
                        state: scene.dataset.sceneState,
                        width: canvas.width,
                        height: canvas.height,
                        contextAvailable: Boolean(gl),
                        contextLost: gl ? gl.isContextLost() : true,
                        drawingBufferWidth: gl ? gl.drawingBufferWidth : 0,
                        drawingBufferHeight: gl ? gl.drawingBufferHeight : 0,
                    };
                }""")
                assert home_scene['state'] in {'ready', 'fallback'}, home_scene
                if home_scene['state'] == 'ready':
                    assert home_scene['width'] > 0 and home_scene['height'] > 0, home_scene
                    assert home_scene['contextAvailable'] and not home_scene['contextLost'], home_scene
                    assert home_scene['drawingBufferWidth'] > 0 and home_scene['drawingBufferHeight'] > 0, home_scene
                assert 'Understand field conditions. Review a crop recommendation. Track the lifecycle.' in page.locator('main').inner_text()
                page.screenshot(path=str(artifacts / 'home_desktop.png'), full_page=True)
                results.append({'path': '/', 'status': home_response.status, 'scene': home_scene['state'],
                                'webgl_context_available': home_scene['contextAvailable']})
                page.goto('http://127.0.0.1:5056/register')
                page.fill('[name=name]', 'Browser Farmer')
                page.fill('[name=email]', 'browser@example.com')
                page.fill('[name=password]', 'secret123')
                page.locator('button[type=submit]').click()
                page.wait_for_url('**/farm/setup')
                page.locator('#btnDetectLocation').click()
                page.wait_for_function("!document.getElementById('mapSelectionSection').classList.contains('d-none')", timeout=15000)
                assert page.locator('#mapSelectionSection').is_visible()
                page.fill('[name=latitude]', '18.5')
                page.fill('[name=longitude]', '73.8')
                page.fill('[name=location_name]', 'Manual test location')
                page.fill('[name=farm_name]', 'Browser Farm')
                # Soil values are required by the setup form. These are synthetic
                # test inputs, not measured field data.
                page.fill('[name=nitrogen]', '90')
                page.fill('[name=phosphorus]', '42')
                page.fill('[name=potassium]', '43')
                page.fill('[name=ph]', '6.5')
                page.locator('#farmSetupForm button[type=submit]').click()
                page.wait_for_url('**/crop-recommendation')
                assert page.locator('#cropForm').is_visible()
                results.append({'path': 'farm-setup-first-crop-planner', 'status': 200})
                page.goto('http://127.0.0.1:5056/dashboard')
                for path in ['/dashboard', '/weather', '/daily-plan', '/seven-day-plan', '/crop-recommendation', '/activities', '/report-problem', '/market', '/history', '/research', '/lifecycle', '/settings']:
                    response = page.goto('http://127.0.0.1:5056' + path)
                    page.wait_for_timeout(250)
                    results.append({'path': path, 'status': response.status})
                nav_paths = ['/dashboard', '/farm', '/crop-recommendation', '/lifecycle', '/activities', '/weather', '/report-problem']
                for path in nav_paths:
                    page.goto('http://127.0.0.1:5056/dashboard')
                    page.locator(f'#appSidebar a[href="{path}"]').click()
                    page.wait_for_load_state('domcontentloaded')
                    assert page.url.endswith(path), page.url
                results.append({'path': 'sidebar-click-navigation', 'status': 200})
                page.goto('http://127.0.0.1:5056/dashboard')
                page.locator('header a[href="/notifications"]').click()
                page.wait_for_url('**/notifications')
                assert 'Notifications' in page.locator('main').inner_text()
                page.goto('http://127.0.0.1:5056/dashboard')
                page.locator('a[href="/daily-plan"]').click()
                page.wait_for_url('**/daily-plan')
                page.goto('http://127.0.0.1:5056/dashboard')
                page.locator('a[href="/seven-day-plan"]').click()
                page.wait_for_url('**/seven-day-plan')
                results.append({'path': 'topbar-and-dashboard-cta-clicks', 'status': 200})
                page.goto('http://127.0.0.1:5056/crop-recommendation')
                weather_response = page.request.get('http://127.0.0.1:5056/api/weather')
                weather_payload = weather_response.json()
                assert weather_response.status in {200, 400}
                assert isinstance(weather_payload.get('success'), bool)
                results.append({
                    'path': 'open-meteo-weather-api',
                    'status': weather_response.status,
                    'state': 'available' if weather_payload['success'] else 'unavailable',
                })
                page.route('**/api/weather', lambda route: route.fulfill(
                    status=200, content_type='application/json',
                    body=json.dumps({'success': True, 'weather': {'current': {'temperature': 27, 'humidity': 66, 'precipitation': 2}}}),
                ))
                page.locator('#btnAutofillWeather').click()
                page.wait_for_function("document.getElementById('inputTemp').value === '27'")
                page.fill('[name=nitrogen]', '90')
                page.fill('[name=phosphorus]', '42')
                page.fill('[name=potassium]', '43')
                page.fill('[name=ph]', '6.5')
                page.locator('#cropForm button[type=submit]').click()
                assert 'ML confidence' in page.locator('main').inner_text()
                assert page.locator('table tbody tr').count() >= 1
                page.locator('section.content-section form button').first.click()
                page.wait_for_url('**/lifecycle?crop=*')
                page.locator('[name=sowing_date]').fill(__import__('datetime').date.today().isoformat())
                page.locator('form').filter(has=page.locator('[name=sowing_date]')).locator('button[type=submit]').click()
                page.wait_for_url('**/lifecycle')
                assert 'Crop stage timeline' in page.locator('main').inner_text()
                lifecycle_scene = page.locator('[data-farm-scene="plant"]')
                page.wait_for_function("document.querySelector('[data-farm-scene=plant]').dataset.sceneState !== 'loading'", timeout=15000)
                assert lifecycle_scene.get_attribute('data-scene-state') in {'ready', 'fallback'}
                page.goto('http://127.0.0.1:5056/report-problem')
                page.fill('[name=symptoms]', 'yellow leaf spots')
                page.fill('[name=farmer_notes]', 'Observed during browser black-box test')
                page.locator('form[action="/report-problem"] button[type=submit]').click()
                page.wait_for_url('**/disease-result/*')
                assert 'Farmer-reported symptoms and reference notes' in page.locator('main').inner_text()
                results.append({'path': 'problem-report-workflow', 'status': 200})
                page.goto('http://127.0.0.1:5056/disease-detection')
                page.fill('[name=crop]', 'Tomato')
                image = io.BytesIO()
                Image.new('RGB', (3, 3), color='green').save(image, format='PNG')
                page.set_input_files('[name=photo]', {'name': 'test-leaf.png', 'mimeType': 'image/png', 'buffer': image.getvalue()})
                page.locator('form[action="/disease-detection"] button[type=submit]').click()
                page.wait_for_load_state('domcontentloaded')
                detection_text = page.locator('main').inner_text()
                assert 'Image screening result' in detection_text
                assert 'not a confirmed diagnosis' in detection_text
                assert '54,306 images' in detection_text
                results.append({'path': 'standalone-disease-detection-workflow', 'status': 200})
                page.goto('http://127.0.0.1:5056/activities')
                page.locator('details summary').click()
                page.fill('#activity-title', 'Browser completed irrigation check')
                page.select_option('#activity-type', 'Irrigation')
                page.fill('#activity-due', __import__('datetime').date.today().isoformat())
                page.fill('#activity-description', 'Visible user-flow activity test')
                page.locator('form[action="/activities/create"] button[type=submit]').click()
                page.wait_for_url('**/activities')
                activity = page.locator('tbody tr').filter(has_text='Browser completed irrigation check')
                assert 'Pending' in activity.inner_text()
                activity.locator('[name=farmer_note]').fill('Completed in browser test')
                activity.get_by_role('button', name='Completed').click()
                page.wait_for_url('**/activities')
                activity = page.locator('tbody tr').filter(has_text='Browser completed irrigation check')
                assert 'Completed' in activity.inner_text()
                assert activity.locator('[name=farmer_note]').input_value() == 'Completed in browser test'
                page.locator('details summary').click()
                page.fill('#activity-title', 'Browser pending task')
                page.select_option('#activity-type', 'Field inspection')
                page.fill('#activity-due', __import__('datetime').date.today().isoformat())
                page.locator('form[action="/activities/create"] button[type=submit]').click()
                page.wait_for_url('**/activities')
                pending_activity = page.locator('tbody tr').filter(has_text='Browser pending task')
                assert 'Pending' in pending_activity.inner_text()
                results.append({'path': 'activity-create-complete-pending-workflow', 'status': 200})
                page.goto('http://127.0.0.1:5056/settings')
                page.fill('#current-password', 'secret123')
                page.fill('#new-password', 'new-secret123')
                page.fill('#confirm-password', 'new-secret123')
                page.locator('form[action="/settings/change-password"] button[type=submit]').click()
                page.wait_for_url('**/login')
                page.fill('[name=email]', 'browser@example.com')
                page.fill('[name=password]', 'new-secret123')
                page.locator('button[type=submit]').click()
                page.wait_for_url('**/dashboard')
                page.locator('aside form[action="/logout"] button[type=submit]').click()
                page.wait_for_url('**/login')
                page.go_back(wait_until='domcontentloaded')
                if page.url.endswith('/dashboard'):
                    assert page.locator('#appSidebar').count() == 0
                page.goto('http://127.0.0.1:5056/dashboard')
                assert page.url.endswith('/login')
                page.fill('[name=email]', 'browser@example.com')
                page.fill('[name=password]', 'new-secret123')
                page.locator('button[type=submit]').click()
                page.wait_for_url('**/dashboard')
                page.set_viewport_size({'width': 768, 'height': 1024})
                page.goto('http://127.0.0.1:5056/dashboard')
                tablet_dimensions = page.evaluate('({width: document.documentElement.scrollWidth, height: document.documentElement.scrollHeight})')
                assert tablet_dimensions['width'] <= 768, tablet_dimensions
                page.set_viewport_size({'width': 390, 'height': 844})
                page.goto('http://127.0.0.1:5056/dashboard')
                page.wait_for_timeout(300)
                dimensions = page.evaluate('({width: document.documentElement.scrollWidth, height: document.documentElement.scrollHeight})')
                assert dimensions['width'] <= 390, dimensions
                assert dimensions['height'] < 5000, dimensions
                page.locator('#sidebarToggle').click()
                assert page.locator('#appSidebar').evaluate("el => el.classList.contains('show')")
                page.locator('#sidebarToggle').click()
                page.wait_for_timeout(400)
                assert page.locator('.dashboard-metrics > div').count() == 4
                assert page.locator('.app-content').bounding_box()['width'] >= 358
                page.screenshot(path=str(artifacts / 'mobile_dashboard.png'), full_page=True)
                browser.close()
        finally:
            server.shutdown()
        report = {'pages': results, 'javascript_errors': errors, 'failed_requests': failed_requests, 'http_errors': bad_responses}
        (artifacts / 'browser_results.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(json.dumps(report))
        if errors or any(item['status'] != 200 for item in results):
            raise SystemExit(1)


if __name__ == '__main__':
    main()
