from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Optional

from app.core.config import settings


@dataclass
class BrowserSnapshot:
    step: int
    url: str
    title: str
    visible_text: str
    screenshot_path: str
    discovered_links: list[str]
    clickable_elements: list[dict[str, str]]
    inputs: list[dict[str, str]]
    toggles: list[dict[str, str]]
    dialogs: list[dict[str, str]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class BrowserHarness:
    def __init__(self, headless: Optional[bool] = None) -> None:
        self.headless = settings.computer_use_headless if headless is None else headless
        self.screenshot_root = Path(settings.computer_use_screenshot_dir).resolve()
        self.screenshot_root.mkdir(parents=True, exist_ok=True)
        self._playwright = None
        self._browser = None

    async def start(self) -> None:
        if self._browser is not None:
            return
        try:
            from playwright.async_api import async_playwright
        except Exception as exc:
            raise RuntimeError(
                "Playwright is not installed. Run `pip install playwright` and `playwright install chromium`."
            ) from exc

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=self.headless)

    async def new_page(self, viewport: Optional[dict[str, int]] = None):
        if self._browser is None:
            await self.start()
        viewport = viewport or {"width": 1440, "height": 960}
        return await self._browser.new_page(viewport=viewport)

    async def close(self) -> None:
        try:
            if self._browser is not None:
                await self._browser.close()
        finally:
            self._browser = None
            if self._playwright is not None:
                await self._playwright.stop()
            self._playwright = None

    async def goto(self, page, url: str) -> None:
        await page.goto(url, wait_until="domcontentloaded")
        await self._stabilize(page)

    async def navigate_page(self, page, url: str, wait_until: str = "domcontentloaded") -> None:
        await page.goto(url, wait_until=wait_until)
        await self._stabilize(page)

    async def click_selector(self, page, selector: str, text_fallback: str | None = None) -> None:
        await self.robust_click(page, selector, text_fallback=text_fallback)

    async def click_text(self, page, text: str) -> None:
        before = await self._state_signature(page)
        locator = page.get_by_text(text, exact=False).first
        await locator.click(timeout=8000)
        await self._stabilize(page)
        await self.wait_for_state_change(page, before)

    async def type_selector(self, page, selector: str, value: str, submit: bool = False) -> None:
        await self.safe_fill(page, selector, value, submit=submit)

    async def search(self, page, query: str) -> None:
        selectors = [
            'input[type="search"]',
            'input[placeholder*="search" i]',
            'input[aria-label*="search" i]',
            'input[name*="search" i]',
            '[role="search"] input',
            'form input[type="text"]',
        ]
        for selector in selectors:
            try:
                await self.safe_fill(page, selector, query, submit=True)
                return
            except Exception:
                continue
        raise RuntimeError("No searchable input found for SEARCH action.")

    async def apply_filter(self, page, filter_text: str) -> None:
        before = await self._state_signature(page)
        candidates = [
            f'label:has-text("{filter_text}")',
            f'button:has-text("{filter_text}")',
            f'[role="button"]:has-text("{filter_text}")',
        ]

        for selector in candidates:
            try:
                await self.robust_click(page, selector, text_fallback=filter_text)
                await self.wait_for_state_change(page, before, allow_no_change=True)
                return
            except Exception:
                continue

        try:
            await self.click_text(page, filter_text)
            return
        except Exception as exc:
            raise RuntimeError(f"Could not apply filter: {filter_text}") from exc

    async def add_to_cart(self, page) -> None:
        before = await self._state_signature(page)
        texts = ["Add to Bag", "Add to Cart", "Add to Basket", "Add"]
        for text in texts:
            try:
                await self.click_text(page, text)
                await self.wait_for_state_change(page, before, allow_no_change=True)
                return
            except Exception:
                continue
        candidates = [
            'button[data-testid*="add" i]',
            'button[name*="add" i]',
            'button[id*="add" i]',
            'button',
            '[role="button"]',
        ]
        for selector in candidates:
            try:
                await self.robust_click(page, selector, text_fallback="Add")
                await self.wait_for_state_change(page, before, allow_no_change=True)
                return
            except Exception:
                continue
        raise RuntimeError("Could not find an add-to-cart style control.")

    async def safe_fill(self, page, selector: str, value: str, submit: bool = False) -> None:
        locator = page.locator(selector).first
        await locator.wait_for(state="visible", timeout=8000)
        await locator.click(timeout=5000)
        await locator.fill(value)
        read_back = await locator.input_value()
        if read_back != value:
            await locator.press("Control+A")
            await locator.fill(value)
        if submit:
            await locator.press("Enter")
        await self._stabilize(page)

    async def safe_toggle(self, page, selector: str, desired: bool = True, text_fallback: str | None = None) -> None:
        locator = page.locator(selector).first
        await locator.wait_for(state="attached", timeout=5000)
        tag = await locator.evaluate("(el) => el.tagName.toLowerCase()")
        input_type = await locator.get_attribute("type")
        el_id = await locator.get_attribute("id")

        if tag == "input" and input_type in {"checkbox", "radio"}:
            try:
                if desired:
                    await locator.check(timeout=5000, force=True)
                else:
                    await locator.uncheck(timeout=5000, force=True)
                await self._stabilize(page)
                return
            except Exception:
                pass

            if el_id:
                label_selector = f'label[for="{el_id}"]'
                await self.robust_click(page, label_selector, text_fallback=text_fallback)
                return

        await self.robust_click(page, selector, text_fallback=text_fallback)

    async def robust_click(self, page, selector: str, text_fallback: str | None = None) -> None:
        errors = []
        before = await self._state_signature(page)

        try:
            locator = page.locator(selector).first
            await locator.wait_for(state="attached", timeout=5000)
            await locator.click(timeout=5000)
            await self._stabilize(page)
            await self.wait_for_state_change(page, before, allow_no_change=True)
            return
        except Exception as exc:
            errors.append(f"normal click failed: {exc}")

        try:
            locator = page.locator(selector).first
            tag = await locator.evaluate("(el) => el.tagName.toLowerCase()")
            input_type = await locator.get_attribute("type")
            el_id = await locator.get_attribute("id")
            cls = (await locator.get_attribute("class")) or ""

            if tag == "input" and (input_type in {"checkbox", "radio"} or "sr-only" in cls):
                if input_type in {"checkbox", "radio"}:
                    try:
                        await locator.check(timeout=5000, force=True)
                        await self._stabilize(page)
                        await self.wait_for_state_change(page, before, allow_no_change=True)
                        return
                    except Exception:
                        pass
                if el_id:
                    label = page.locator(f'label[for="{el_id}"]').first
                    if await label.count() > 0:
                        await label.click(timeout=5000)
                        await self._stabilize(page)
                        await self.wait_for_state_change(page, before, allow_no_change=True)
                        return
        except Exception as exc:
            errors.append(f"toggle/label click failed: {exc}")

        if text_fallback:
            try:
                locator = page.get_by_text(text_fallback, exact=False).first
                await locator.click(timeout=5000)
                await self._stabilize(page)
                await self.wait_for_state_change(page, before, allow_no_change=True)
                return
            except Exception as exc:
                errors.append(f"text click failed: {exc}")

        try:
            locator = page.locator(selector).first
            await locator.click(timeout=5000, force=True)
            await self._stabilize(page)
            await self.wait_for_state_change(page, before, allow_no_change=True)
            return
        except Exception as exc:
            errors.append(f"force click failed: {exc}")

        try:
            locator = page.locator(selector).first
            await locator.evaluate("(el) => el.click()")
            await self._stabilize(page)
            await self.wait_for_state_change(page, before, allow_no_change=True)
            return
        except Exception as exc:
            errors.append(f"js click failed: {exc}")

        raise RuntimeError(" | ".join(errors))

    async def wait_for_state_change(self, page, before: dict[str, str], allow_no_change: bool = False) -> None:
        for _ in range(8):
            await page.wait_for_timeout(250)
            after = await self._state_signature(page)
            if after != before:
                return
        if not allow_no_change:
            raise RuntimeError("No observable state change after action.")

    async def capture_current_page(self, page, app_name: str | None, step: int = 1) -> BrowserSnapshot:
        await self._stabilize(page)
        return await self._capture_page(page, step, app_name)

    async def get_page_links(self, page) -> list[str]:
        return await self._extract_candidate_links(page)

    async def _state_signature(self, page) -> dict[str, str]:
        try:
            title = await page.title()
        except Exception:
            title = ""
        try:
            url = page.url
        except Exception:
            url = ""
        try:
            text = await page.evaluate("() => (document.body ? document.body.innerText.slice(0, 500) : '')")
        except Exception:
            text = ""
        return {"url": url, "title": title, "text": text}

    async def capture_journey(
        self,
        start_url: str,
        max_steps: int = 4,
        app_name: str | None = None,
        pause_for_manual_login: bool = False,
        pause_before_close: bool = False,
    ) -> list[BrowserSnapshot]:
        snapshots: list[BrowserSnapshot] = []

        page = await self.new_page()
        try:
            await page.goto(start_url, wait_until="domcontentloaded")
            await self._stabilize(page)

            if pause_for_manual_login:
                print("\n[computer-use] Manual login pause is enabled.")
                print("[computer-use] Log in manually in the opened browser window.")
                input("[computer-use] After login completes and the app is ready, press Enter here to continue...\n")
                await self._stabilize(page)

            snapshots.append(await self._capture_page(page, 1, app_name))

            if pause_before_close:
                print("\n[computer-use] Workflow finished. Browser will stay open for review.")
                input("[computer-use] Press Enter to close the browser...\n")

            return snapshots
        finally:
            await page.close()

    async def _stabilize(self, page) -> None:
        try:
            await page.wait_for_load_state("domcontentloaded")
        except Exception:
            pass
        try:
            await page.wait_for_timeout(settings.computer_use_step_delay_ms)
        except Exception:
            pass

    async def _capture_page(self, page, step: int, app_name: str | None) -> BrowserSnapshot:
        safe_name = (app_name or "computer_use").replace(" ", "_").replace("/", "_").replace("\\", "_")
        screenshot_path = self.screenshot_root / f"{safe_name}_step_{step}.png"

        title = ""
        visible_text = ""
        discovered_links = []
        clickable_elements = []
        inputs = []
        toggles = []
        dialogs = []

        try:
            title = await page.title()
        except Exception:
            pass

        try:
            visible_text = await page.evaluate("""() => {
                const text = document.body ? document.body.innerText || '' : '';
                return text.replace(/\s+/g, ' ').trim().slice(0, 5000);
            }""")
        except Exception:
            pass

        try:
            discovered_links = await self._extract_candidate_links(page)
        except Exception:
            pass

        try:
            clickable_elements = await page.evaluate("""() => {
                const nodes = Array.from(document.querySelectorAll('button, a, label, [role="button"], input[type="button"], input[type="submit"]')).slice(0, 60);
                return nodes.map((el, idx) => ({
                    index: String(idx + 1),
                    text: (el.innerText || el.value || el.getAttribute('aria-label') || el.getAttribute('title') || '').trim().slice(0, 120),
                    tag: el.tagName.toLowerCase(),
                    forAttr: el.getAttribute('for') || '',
                    selector_hint: el.id ? `#${el.id}` : (el.getAttribute('data-testid') ? `[data-testid="${el.getAttribute('data-testid')}"]` : el.tagName.toLowerCase())
                })).filter(x => x.text || x.selector_hint || x.forAttr);
            }""")
        except Exception:
            pass

        try:
            inputs = await page.evaluate("""() => {
                const nodes = Array.from(document.querySelectorAll('input, textarea, select')).slice(0, 25);
                return nodes.map((el, idx) => ({
                    index: String(idx + 1),
                    type: (el.getAttribute('type') || el.tagName || '').toLowerCase(),
                    name: (el.getAttribute('name') || '').slice(0, 80),
                    placeholder: (el.getAttribute('placeholder') || '').slice(0, 80),
                    selector_hint: el.id ? `#${el.id}` : (el.getAttribute('name') ? `${el.tagName.toLowerCase()}[name="${el.getAttribute('name')}"]` : el.tagName.toLowerCase())
                }));
            }""")
        except Exception:
            pass

        try:
            toggles = await page.evaluate("""() => {
                const nodes = Array.from(document.querySelectorAll('input[type="checkbox"], input[type="radio"], [role="switch"]')).slice(0, 25);
                return nodes.map((el, idx) => ({
                    index: String(idx + 1),
                    tag: el.tagName.toLowerCase(),
                    type: el.getAttribute('type') || '',
                    id: el.id || '',
                    ariaLabel: el.getAttribute('aria-label') || '',
                    selector_hint: el.id ? `#${el.id}` : el.tagName.toLowerCase()
                }));
            }""")
        except Exception:
            pass

        try:
            dialogs = await page.evaluate("""() => {
                const nodes = Array.from(document.querySelectorAll('[role="dialog"], dialog, [aria-modal="true"]')).slice(0, 10);
                return nodes.map((el, idx) => ({
                    index: String(idx + 1),
                    text: (el.innerText || '').trim().slice(0, 160),
                    selector_hint: el.id ? `#${el.id}` : (el.getAttribute('role') ? `[role="${el.getAttribute('role')}"]` : el.tagName.toLowerCase())
                }));
            }""")
        except Exception:
            pass

        try:
            await page.screenshot(path=str(screenshot_path), full_page=True)
        except Exception:
            pass

        return BrowserSnapshot(
            step=step,
            url=getattr(page, "url", ""),
            title=title,
            visible_text=visible_text,
            screenshot_path=str(screenshot_path),
            discovered_links=discovered_links[:12],
            clickable_elements=clickable_elements[:20],
            inputs=inputs[:10],
            toggles=toggles[:10],
            dialogs=dialogs[:5],
        )

    async def _extract_candidate_links(self, page) -> list[str]:
        try:
            links = await page.evaluate("""() => {
                const hrefs = [];
                for (const el of Array.from(document.querySelectorAll('a[href]')).slice(0, 120)) {
                    const href = el.href || el.getAttribute('href');
                    if (href && !href.startsWith('javascript:')) {
                        hrefs.push(href);
                    }
                }
                return hrefs;
            }""")
        except Exception:
            links = []

        deduped = []
        seen = set()
        for href in links:
            if href not in seen:
                seen.add(href)
                deduped.append(href)
        return deduped[:30]
