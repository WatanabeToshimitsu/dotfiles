// Reads start and end dates of the items on a Notion timeline view from where their bars are drawn.
// Paste into one javascript_tool call on the view's page, then run `await notionTimeline()` in the next call.
// The header's highlighted today label anchors the scale.
window.notionTimeline = async () => {
  const view = document.querySelector('.notion-timeline-view');
  const firstRow = view?.querySelector('.notion-timeline-item-row');
  if (!firstRow) return { ok: false, why: 'no timeline items on this page' };
  // Notion loads more rows only when the view is scrolled to its end.
  const scroller = firstRow.closest('.notion-scroller.vertical');
  const bars = () => view.querySelectorAll('.notion-timeline-item-row .notion-page-block');
  for (let seen = -1, stable = 0; stable < 2; ) {
    stable = seen === bars().length ? stable + 1 : 0;
    seen = bars().length;
    scroller.scrollTop = scroller.scrollHeight;
    await new Promise((r) => setTimeout(r, 2500));
  }
  scroller.scrollTop = 0;
  await new Promise((r) => setTimeout(r, 500));
  const top = firstRow.getBoundingClientRect().top;
  const center = (e) => {
    const b = e.getBoundingClientRect();
    return b.left + b.width / 2;
  };
  const header = [...view.querySelectorAll('*')].filter(
    (e) => e.children.length === 0 && /^\d{1,2}$/.test((e.innerText || '').trim()) && e.getBoundingClientRect().top < top,
  );
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  // The today label is the widest header number with today's day of month; a week tick can share its text.
  const pill = header
    .filter((e) => +e.innerText.trim() === today.getDate())
    .sort((a, b) => b.getBoundingClientRect().width - a.getBoundingClientRect().width)[0];
  if (!pill) return { ok: false, why: 'today label not found in the header' };
  const ticks = header
    .filter((e) => e !== pill)
    .map((e) => ({ x: center(e), day: +e.innerText.trim() }))
    .sort((a, b) => a.x - b.x);
  if (ticks.length < 3) return { ok: false, why: 'too few header ticks' };
  const gaps = ticks.slice(1).map((t, i) => t.x - ticks[i].x).sort((a, b) => a - b);
  const perDay = gaps[Math.floor(gaps.length / 2)] / 7;
  const x0 = center(pill);
  const at = (offset) => {
    const d = new Date(today);
    d.setDate(d.getDate() + offset);
    return d;
  };
  const iso = (offset) => {
    const d = at(offset);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  };
  // Every tick must land on the day its label names; this rejects a wrong anchor and non-weekly zoom levels.
  const off = ticks.filter((t) => at(Math.round((t.x - x0) / perDay)).getDate() !== t.day);
  if (off.length) return { ok: false, why: `${off.length} of ${ticks.length} header ticks do not match the computed dates` };
  const items = [...bars()].map((bar) => {
    const b = bar.getBoundingClientRect();
    const row = bar.closest('.notion-timeline-item-row');
    return {
      title: row.querySelector('.notion-timeline-item-properties')?.innerText.split('\n')[0].trim() || '',
      start: iso(Math.round((b.left - x0) / perDay)),
      end: iso(Math.round((b.right - x0) / perDay) - 1),
    };
  });
  return { ok: true, perDay, items };
};
'notionTimeline ready';
