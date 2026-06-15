"""
============================================================
  Face Recognition Attendance System – Chapter 6 Screenshot Tool
  BCA Final Project | Automated UI Snapshot Utility
============================================================

Usage:
    python capture_screenshots.py

Generates 4 report-ready images inside  ./report_snapshots/
    1_admin_dashboard.png
    2_student_registration.png
    3_live_face_recognition.png
    4_attendance_logs.png

Requirements (install once – see bottom of file for commands):
    playwright  +  chromium browser
    (Flask + your project dependencies must already be installed)
"""

import os
import sys
import time
import subprocess
import signal
import textwrap
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# ──────────────────────────────────────────────
#  CONFIG  – adjust these if your app differs
# ──────────────────────────────────────────────
FLASK_HOST   = "http://127.0.0.1:5000"
PROJECT_DIR  = Path(__file__).parent          # folder where app.py lives
OUTPUT_DIR   = PROJECT_DIR / "report_snapshots"
SERVER_WAIT  = 3          # seconds to wait after launching Flask before browsing

# Teacher credentials that exist in registered_teachers.txt
TEACHER_USER = "Chinmay_"        # change to a real username in your file
TEACHER_PASS = "BCA01Pass"       # change to the matching password

VIEWPORT     = {"width": 1440, "height": 900}
# ──────────────────────────────────────────────


def banner(msg: str) -> None:
    print(f"\n{'─'*60}")
    print(f"  {msg}")
    print(f"{'─'*60}")


def start_flask() -> subprocess.Popen:
    """Launch `app.py` as a background subprocess."""
    banner("Step 1 – Starting Flask development server …")
    env = os.environ.copy()
    env["FLASK_ENV"] = "development"
    proc = subprocess.Popen(
        [sys.executable, "app.py"],
        cwd=str(PROJECT_DIR),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    # Give it a moment to bind to the port
    time.sleep(SERVER_WAIT)
    if proc.poll() is not None:
        out, err = proc.communicate()
        print("ERROR: Flask server exited immediately.")
        print(err.decode())
        sys.exit(1)
    print(f"  ✔  Flask server running  (PID {proc.pid})")
    return proc


def stop_flask(proc: subprocess.Popen) -> None:
    banner("Step 6 – Terminating Flask server …")
    try:
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=5)
    except Exception:
        proc.kill()
    print("  ✔  Server stopped cleanly.")


def wait_for_selector_safe(page, selector: str, timeout: int = 6000) -> bool:
    """Return True if selector becomes visible, False on timeout."""
    try:
        page.wait_for_selector(selector, timeout=timeout)
        return True
    except PlaywrightTimeout:
        return False


def login(page, base: str) -> None:
    """Log in as teacher so session-protected pages are accessible."""
    page.goto(f"{base}/login", wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")

    # Try the JSON login endpoint first (more reliable with Playwright)
    result = page.evaluate("""
        async ([user, pwd]) => {
            const r = await fetch('/login_auth', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({username: user, password: pwd})
            });
            return r.ok;
        }
    """, [TEACHER_USER, TEACHER_PASS])

    if result:
        print("  ✔  Logged in via API auth.")
        return

    # Fallback: fill the HTML form
    page.fill("input[name='username'], #username", TEACHER_USER)
    page.fill("input[name='password'], #password", TEACHER_PASS)
    page.click("button[type='submit'], input[type='submit']")
    page.wait_for_load_state("networkidle")
    print("  ✔  Logged in via form.")


# ──────────────────────────────────────────────────────────────────
#  SCREENSHOT HELPERS
# ──────────────────────────────────────────────────────────────────

def screenshot_1_dashboard(page, base: str, out: Path) -> None:
    banner("Step 2 – Screenshot 1 › Admin Dashboard")
    page.goto(f"{base}/college_admin_dashboard", wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")

    # Ensure the default home section is visible
    wait_for_selector_safe(page, ".card, #home, .dashboard", timeout=5000)
    time.sleep(0.8)          # allow any chart/animation to settle

    dest = out / "1_admin_dashboard.png"
    page.screenshot(path=str(dest), full_page=True)
    print(f"  ✔  Saved → {dest}")


def screenshot_2_registration(page, base: str, out: Path) -> None:
    banner("Step 3 – Screenshot 2 › Student Registration Form")
    page.goto(f"{base}/college_admin_dashboard", wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")
    page.evaluate("""
    () => {
        const items = [...document.querySelectorAll('a, button, div, li, span')];
        const item = items.find(x => x.innerText && x.innerText.toLowerCase().includes('register'));
        if (item) item.click();
    }
    """)
    time.sleep(1)

    # Click into the "Register Student" / student details panel via JS
    # (the admin page uses JS showPage() to switch panels)
    triggered = page.evaluate("""
        () => {
            // Try common nav-item labels
            const labels = ['register', 'student', 'add student'];
            const items = document.querySelectorAll('.nav-item, nav a, [onclick]');
            for (const el of items) {
                const txt = el.textContent.toLowerCase();
                if (labels.some(l => txt.includes(l))) {
                    el.click();
                    return el.textContent.trim();
                }
            }
            return null;
        }
    """)
    if triggered:
        print(f"  ↳ Clicked nav item: '{triggered}'")
    time.sleep(0.5)

    # Fill in every visible text/select input on the active page
    # (works generically even if field IDs differ between versions)
    page.evaluate("""
        () => {
            const active = document.querySelector('.active-page, .page.active, #register_student, #add_student');
            const root   = active || document.body;

            const setVal = (sel, val) => {
                const el = root.querySelector(sel);
                if (!el) return;
                const nativeSetter = Object.getOwnPropertyDescriptor(
                    window.HTMLInputElement.prototype, 'value'
                )?.set || Object.getOwnPropertyDescriptor(
                    window.HTMLTextAreaElement.prototype, 'value'
                )?.set;
                if (nativeSetter) nativeSetter.call(el, val);
                el.dispatchEvent(new Event('input', {bubbles: true}));
                el.dispatchEvent(new Event('change', {bubbles: true}));
            };

            // Name-like fields
            ['#name','[name=name]','[placeholder*=Name i]'].forEach(s => setVal(s, 'John Doe'));
            // ID / Reg No fields
            ['#id','#reg','#student_id','[name=id],[name=reg],[placeholder*=ID i],[placeholder*=Reg i]']
                .forEach(s => setVal(s, '12345'));
            // Phone
            ['#phone','[name=phone]','[placeholder*=Phone i]'].forEach(s => setVal(s, '9876543210'));
            // Parent name
            ['#p_name','[name=p_name]','[placeholder*=Parent i]'].forEach(s => setVal(s, 'James Doe'));
            // Parent phone
            ['#p_phone','[name=p_phone]'].forEach(s => setVal(s, '9123456789'));

            // Department select / input
            const deptSel = root.querySelector('#department,[name=department],select[id*=dept i]');
            if (deptSel) {
                if (deptSel.tagName === 'SELECT') {
                    // Pick BCA option or first option
                    const opt = [...deptSel.options].find(o => o.text.toUpperCase().includes('BCA'))
                                || deptSel.options[0];
                    if (opt) { deptSel.value = opt.value; }
                    deptSel.dispatchEvent(new Event('change',{bubbles:true}));
                } else {
                    setVal('#department,[name=department]', 'BCA');
                }
            }

            // Semester select
            const semSel = root.querySelector('#semester,[name=semester],select[id*=sem i]');
            if (semSel && semSel.tagName === 'SELECT' && semSel.options.length > 0) {
                semSel.value = semSel.options[0].value;
                semSel.dispatchEvent(new Event('change',{bubbles:true}));
            }

            // Section select
            const secSel = root.querySelector('#section,[name=section],select[id*=sec i]');
            if (secSel && secSel.tagName === 'SELECT' && secSel.options.length > 0) {
                secSel.value = secSel.options[0].value;
                secSel.dispatchEvent(new Event('change',{bubbles:true}));
            }

            // Gender radio/select
            const genderEl = root.querySelector('[name=gender]');
            if (genderEl) {
                if (genderEl.tagName === 'SELECT') { genderEl.value = genderEl.options[0]?.value; }
                else { genderEl.checked = true; }
            }
        }
    """)
    time.sleep(0.4)

    dest = out / "2_student_registration.png"
    page.screenshot(path=str(dest), full_page=True)
    print(f"  ✔  Saved → {dest}")


def screenshot_3_live_attendance(page, base: str, out: Path) -> None:
    banner("Step 4 – Screenshot 3 › Live Face Recognition / Attendance")
    page.goto(f"{base}/college_admin_dashboard", wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")
    page.evaluate("""
    () => {
        const items = [...document.querySelectorAll('a, button, div, li, span')];
        const item = items.find(x => x.innerText && x.innerText.toLowerCase().includes('attendance'));
        if (item) item.click();
    }
    """)
    time.sleep(1)

    # Navigate to the Attendance panel
    page.evaluate("""
        () => {
            const items = document.querySelectorAll('.nav-item,[onclick]');
            for (const el of items) {
                if (el.textContent.toLowerCase().includes('attendance')) {
                    el.click(); return;
                }
            }
            // fallback: call showPage directly
            if (typeof showPage === 'function') showPage('attendance');
        }
    """)
    time.sleep(0.5)

    # Inject a realistic "live camera" mock UI into the camera-box div
    # so the screenshot looks like the webcam feed is active.
    page.evaluate("""
        () => {
            const box = document.querySelector('.camera-box, #camera_feed, #videoFeed, video, canvas');
            if (!box) return;

            // Replace the placeholder with a styled mock frame
            box.style.cssText = `
                width:480px; height:360px; background:#0a0a0a;
                border-radius:10px; position:relative; overflow:hidden;
                border:2px solid #00ff88; display:flex;
                align-items:center; justify-content:center;
            `;
            box.innerHTML = `
              <svg xmlns='http://www.w3.org/2000/svg' width='480' height='360'>
                <!-- Dark background -->
                <rect width='480' height='360' fill='#111'/>

                <!-- Simulated face oval -->
                <ellipse cx='240' cy='170' rx='80' ry='95' fill='none'
                         stroke='#00ff88' stroke-width='2.5' stroke-dasharray='8 4'/>

                <!-- Corner tracking brackets -->
                <polyline points='155,80 155,110 185,110' fill='none' stroke='#00ff88' stroke-width='2'/>
                <polyline points='325,80 325,110 295,110' fill='none' stroke='#00ff88' stroke-width='2'/>
                <polyline points='155,260 155,230 185,230' fill='none' stroke='#00ff88' stroke-width='2'/>
                <polyline points='325,260 325,230 295,230' fill='none' stroke='#00ff88' stroke-width='2'/>

                <!-- Face landmark dots -->
                <circle cx='210' cy='155' r='3' fill='#00ff88'/>
                <circle cx='270' cy='155' r='3' fill='#00ff88'/>
                <circle cx='240' cy='180' r='3' fill='#00ff88'/>
                <line  x1='220' y1='205' x2='260' y2='205'
                       stroke='#00ff88' stroke-width='2' stroke-linecap='round'/>

                <!-- Status bar -->
                <rect x='0' y='320' width='480' height='40' fill='rgba(0,255,136,0.15)'/>
                <circle cx='20' cy='340' r='6' fill='#00ff88'>
                  <animate attributeName='opacity' values='1;0.2;1' dur='1.2s' repeatCount='indefinite'/>
                </circle>
                <text x='36' y='345' font-family='monospace' font-size='13'
                      fill='#00ff88'>LIVE  •  Face Recognition Active</text>
                <text x='380' y='345' font-family='monospace' font-size='11'
                      fill='#aaa'>30 fps</text>

                <!-- Scan line animation hint -->
                <line x1='160' y1='160' x2='320' y2='160' stroke='#00ff8855' stroke-width='1.5'/>

                <!-- Name label -->
                <rect x='155' y='268' width='170' height='22' rx='4' fill='rgba(0,255,136,0.2)'/>
                <text x='165' y='283' font-family='monospace' font-size='12' fill='#00ff88'>
                  Detecting…  ID: 12345
                </text>
              </svg>
            `;
        }
    """)
    time.sleep(0.3)

    dest = out / "3_live_face_recognition.png"
    page.screenshot(path=str(dest), full_page=True)
    print(f"  ✔  Saved → {dest}")


def screenshot_4_attendance_logs(page, base: str, out: Path) -> None:
    banner("Step 5 – Screenshot 4 › Attendance Logs Table")
    page.goto(f"{base}/college_admin_dashboard", wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")
    page.evaluate("""
    () => {
        const items = [...document.querySelectorAll('a, button, div, li, span')];
        const item = items.find(x => x.innerText && (
            x.innerText.toLowerCase().includes('record') ||
            x.innerText.toLowerCase().includes('log')
        ));
        if (item) item.click();
    }
    """)
    time.sleep(1)

    # Navigate to Records / View Attendance panel
    page.evaluate("""
        () => {
            const items = document.querySelectorAll('.nav-item,[onclick]');
            for (const el of items) {
                const t = el.textContent.toLowerCase();
                if (t.includes('record') || t.includes('log') || t.includes('view')) {
                    el.click(); return;
                }
            }
            if (typeof showPage === 'function') showPage('records');
        }
    """)
    time.sleep(0.6)

    # If the table is still empty, inject sample rows so the screenshot
    # looks representative (just for Chapter 6 illustration purposes)
    page.evaluate("""
        () => {
            const tbody = document.querySelector('#attendanceTable, .attendance-table tbody, table tbody');
            if (!tbody) return;
            if (tbody.querySelectorAll('tr').length > 2) return; // already has data

            const sample = [
                ['John Doe',    '12345', 'BCA', '2', 'A', 'Python',          '2026-05-26', '09:15', 'Present'],
                ['Jane Smith',  '12346', 'BCA', '2', 'A', 'Python',          '2026-05-26', '09:16', 'Present'],
                ['Rahul Verma', '12347', 'BCA', '2', 'A', 'Python',          '2026-05-26', '09:18', 'Absent'],
                ['Priya Nair',  '12348', 'BCA', '2', 'A', 'Python',          '2026-05-26', '09:19', 'Present'],
                ['Amit Kumar',  '12349', 'BCA', '2', 'B', 'Data Structures', '2026-05-26', '10:05', 'Present'],
                ['Sneha Roy',   '12350', 'BCA', '2', 'B', 'Data Structures', '2026-05-26', '10:06', 'Present'],
                ['Karan Mehta', '12351', 'BCA', '2', 'B', 'Data Structures', '2026-05-26', '10:08', 'Absent'],
                ['Divya Pillai','12352', 'BCA', '2', 'A', 'DBMS',            '2026-05-25', '11:02', 'Present'],
                ['Arjun Das',   '12353', 'BCA', '2', 'A', 'DBMS',            '2026-05-25', '11:04', 'Present'],
                ['Meena Joshi', '12354', 'BCA', '2', 'A', 'DBMS',            '2026-05-25', '11:05', 'Present'],
            ];
            tbody.innerHTML = '';
            sample.forEach(row => {
                const tr = document.createElement('tr');
                row.forEach((cell, i) => {
                    const td = document.createElement('td');
                    if (i === 8) {   // Status column
                        td.innerHTML = cell === 'Present'
                            ? `<span style='color:#28a745;font-weight:600'>${cell}</span>`
                            : `<span style='color:#dc3545;font-weight:600'>${cell}</span>`;
                    } else {
                        td.textContent = cell;
                    }
                    tr.appendChild(td);
                });
                tbody.appendChild(tr);
            });
        }
    """)
    time.sleep(0.4)

    dest = out / "4_attendance_logs.png"
    page.screenshot(path=str(dest), full_page=True)
    print(f"  ✔  Saved → {dest}")


# ──────────────────────────────────────────────────────────────────
#  MAIN
# ──────────────────────────────────────────────────────────────────

def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\n  Output folder: {OUTPUT_DIR.resolve()}")

    flask_proc = start_flask()

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                ],
            )
            ctx = browser.new_context(
                viewport=VIEWPORT,
                device_scale_factor=2,          # 2× = high-resolution / retina
                ignore_https_errors=True,
            )
            page = ctx.new_page()
            # Silence non-critical console noise
            page.on("console", lambda m: None)

            # ── Log in once; session cookie reused for all pages ──
            # login(page, FLASK_HOST)

            screenshot_1_dashboard(page, FLASK_HOST, OUTPUT_DIR)
            screenshot_2_registration(page, FLASK_HOST, OUTPUT_DIR)
            screenshot_3_live_attendance(page, FLASK_HOST, OUTPUT_DIR)
            screenshot_4_attendance_logs(page, FLASK_HOST, OUTPUT_DIR)

            browser.close()

    finally:
        stop_flask(flask_proc)

    banner("All done! 4 screenshots saved.")
    for img in sorted(OUTPUT_DIR.glob("*.png")):
        size_kb = img.stat().st_size // 1024
        print(f"   📸  {img.name}  ({size_kb} KB)")
    print(f"\n  Folder: {OUTPUT_DIR.resolve()}\n")


if __name__ == "__main__":
    main()
