# Recording reference

`ab` below stands for `agent-browser --session <name> --headed --idle-timeout 0`.
Pass exactly these options on every command, in the lead and the subagent: a
command whose launch options differ relaunches the browser on `about:blank`
and loses the login. `--idle-timeout 0` stops the daemon from closing the
logged-in browser after an hour of inactivity.

## Browser and login

```bash
memgate run -- <dev command>          # background; agent-browser passes through memgate itself
ab open <app url>
```

Ask the user to log in in that window and to say when they are done; then
confirm with `ab get url` and a snapshot that the target page is open. Close consent banners with their most private option. Scroll the
target area into view before `record start` and keep it there.

## Failure mock

Replace `TARGET`, `METHOD`, `STATUS`, and `BODY`. Install the guard first, then
the mock; a reload removes the mock but not the guard. Install one mock per
page load; reload before mocking another scene.

```bash
ab network route "<absolute target url>" --abort
ab eval "$(cat <work-dir>/mock.js)"
```

```js
(() => {
  // Why not wrap again: a second install would also keep mocking the first target.
  if ('__evidenceMock' in window) throw new Error('reload before installing another mock');
  const TARGET = new URL('TARGET', location.href).href, METHOD = 'METHOD';
  const fake = { readyState: 4, status: STATUS, statusText: 'Mocked', responseText: 'BODY' };
  fake.response = fake.responseText;
  const hit = (method, url) =>
    window.__evidenceMock && method.toUpperCase() === METHOD && new URL(url, location.href).href === TARGET;
  const { open, send } = XMLHttpRequest.prototype;
  XMLHttpRequest.prototype.open = function (method, url, ...rest) {
    Object.keys(fake).forEach((key) => delete this[key]);
    this.__mocked = hit(method, String(url));
    return open.call(this, method, url, ...rest);
  };
  XMLHttpRequest.prototype.send = function (body) {
    if (!this.__mocked) return send.call(this, body);
    for (const [key, value] of Object.entries(fake)) {
      Object.defineProperty(this, key, { value, configurable: true });
    }
    // Why not fire only load: apps waiting on readystatechange or loadend hang.
    setTimeout(() => ['readystatechange', 'load', 'loadend'].forEach((type) => this.dispatchEvent(new Event(type))), 300);
  };
  const realFetch = window.fetch;
  window.fetch = (input, init = {}) =>
    hit(init.method || input.method || 'GET', input.url || String(input))
      ? new Promise((done) => setTimeout(() => done(new Response(fake.responseText, { status: fake.status })), 300))
      : realFetch(input, init);
  window.__evidenceMock = true;
})();
```

Prove it before recording. Each probe runs in the page and writes nothing:
a miss on the target is aborted by the guard and shows `status: 0`.

```js
((method, url) => new Promise((done) => {
  const x = new XMLHttpRequest(), seen = [];
  ['readystatechange', 'load', 'loadend'].forEach((type) => x.addEventListener(type, () => {
    seen.push(`${type}:${x.readyState}`);
    if (type === 'loadend') done({ seen, status: x.status, body: x.responseText });
  }));
  x.open(method, url);
  x.send(method === 'GET' ? null : '{}');
  setTimeout(() => done({ seen, timedOut: true }), 3000);
}))('METHOD', 'TARGET')
```

Expect `seen` to end with `readystatechange:4`, `load:4`, `loadend:4`, and
`STATUS` and `BODY`. Run the same probe as `('GET', location.href)` and expect
the real page status: the mock does not touch other requests. If the app uses `fetch`, also check
`fetch('TARGET', { method: 'METHOD' }).then((r) => r.status)`. Afterwards
`ab network requests --filter <path>` shows only aborted or mocked calls.

Cleanup: `ab reload` to drop the wrappers, then `ab network unroute`. Why not
unroute first: a retry from the old page would then reach the server.

## One take

```bash
ab record start <work-dir>/<scene>-raw.mp4 --cursor
ab wait 1500
ab get box "<selector inside the target widget>"   # aim at the box centre
ab mouse move <x> <y> --duration 700 --steps 35
ab wait 400
ab mouse down && ab mouse up
ab wait --text "<result text>" --timeout 15000      # or a selector; exit 1 ends the take
ab mouse move <beside the result> --duration 600 --steps 30
ab wait 1500
ab record stop
```

Scope selectors to the widget when the page has same-named controls. Type
with `ab keyboard type` after focusing the field by a pointer press, not
`fill`, so typing is visible.

## Checks

```bash
ffmpeg -v error -i <final>.mp4 -vf "fps=1.5,scale=440:-1,tile=6x5" <work-dir>/<scene>-sheet-%02d.png
ffmpeg -v error -ss <t> -i <final>.mp4 -frames:v 1 -vf "crop=<w>:<h>:<x>:<y>" <work-dir>/<scene>-<t>.png
ffmpeg -hide_banner -i <final>.mp4 -vf freezedetect=n=0.00005:d=1.3 -map 0:v -f null - 2>&1 | grep freeze_
ffprobe -v error -show_entries format=duration -of csv=p=0 <final>.mp4
```

Open the sheet and each crop as images. Pick `<t>` from the sheet; the crop
is at full resolution, so read message text from it.
