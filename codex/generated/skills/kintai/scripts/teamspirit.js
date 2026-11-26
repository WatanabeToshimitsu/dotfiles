// Helpers for the TeamSpirit attendance page (AtkWorkTimeView) opened as the top-level Visualforce page.
// Paste this file into one javascript_tool call after each page load, then make one ks.* call per javascript_tool call.
// Results carry lengths instead of report text, because the tool's output filter blocks some text.
window.ks = (() => {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const until = async (f, ms = 8000) => {
    for (let t = 0; t < ms; t += 200) {
      const v = f();
      if (v) return v;
      await sleep(200);
    }
    return null;
  };
  const data = () => teasp.viewPoint.graph.pouch.dataObj;
  const dialogs = () => [...document.querySelectorAll('.dijitDialog')].filter((e) => e.offsetParent !== null);
  const label = (root, text) =>
    [...root.querySelectorAll('*')].find((e) => e.children.length === 0 && (e.innerText || '').trim() === text);
  const hm = (min) => `${Math.floor(min / 60)}:${String(min % 60).padStart(2, '0')}`;
  const heading = (date) => {
    const [y, m, d] = date.split('-').map(Number);
    return `${y}年${m}月${d}日`;
  };
  const now = new Date();
  const today = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
  // save() presses 登録 only for the dialog that the last successful fill() or allowance() prepared.
  let pending = null;

  const day = (date) => {
    const d = data();
    const rec = d.days[date] || {};
    const note = rec.workNote || '';
    return {
      date,
      kind: rec.deco?.title || '',
      workDay: rec.dayType === 0,
      realTime: hm(rec.real?.workRealTime || 0),
      location: (d.workLocations.find((l) => l.obj.Id === rec.workLocationId) || {}).obj?.Name || '',
      works: d.works.filter((w) => w.date === date).map((w) => `${w.job.code} ${hm(w.time)}`),
      allowances: d.allowanceDetails.filter((a) => a.date === date).length,
      noteLength: note.length,
      noteLines: note ? note.split('\n').length : 0,
      warning: !!document.querySelector(`#dailyWorkCell${date} .pp_exclamatio2`),
    };
  };

  const cancel = async () => {
    pending = null;
    for (const dlg of dialogs()) label(dlg, 'キャンセル')?.click();
    return { ok: !!(await until(() => !dialogs().length, 3000)) };
  };
  const fail = async (why) => {
    await cancel();
    return { ok: false, why };
  };

  const guarded = (f) => async (...args) => {
    try {
      return await f(...args);
    } catch (e) {
      return fail(`error: ${e.message}`);
    }
  };
  const refuse = (date) => {
    if (dialogs().length) return 'a dialog is already open';
    if (!document.getElementById('dateRow' + date)) return 'date is not on the shown month';
    if (date > today) return 'date is after today';
    return null;
  };

  // Opens the work dialog and enters the day's real work time on one job with the report text. Leaves it open for save().
  const fill = guarded(async (date, code, note) => {
    const why = refuse(date) || (day(date).works.length && 'day already has work entries') || (day(date).noteLength && 'day already has a report');
    if (why) return { ok: false, why };
    document.querySelector(`#dailyWorkCell${date} .png-add`).click();
    const dlg = await until(() => dialogs().find((e) => e.id === 'dialogWorkBalance'));
    if (!dlg) return fail('work dialog did not open');
    if (!dlg.innerText.includes(heading(date))) return fail('dialog shows another date');
    const real = dlg.innerText.match(/実労働時間：(\d+:\d\d)/)?.[1];
    if (!real || real === '0:00') return fail('no real work time on this day');
    const codeInput = [...dlg.querySelectorAll('input[type=hidden]')].find((i) => i.value.startsWith(code + '|'));
    if (!codeInput) return fail(`job ${code} is not in the dialog`);
    const row = codeInput.closest('tr').querySelector('[id^=empWorkSeq]').id.replace('empWorkSeq', '');
    document.getElementById('btnClock2' + row).click();
    const time = await until(() => document.getElementById('empInputTime' + row));
    if (!time) return fail('time field did not appear');
    // The widgets read these values on change and blur, as with typed input.
    for (const [el, value] of [[time, real], [document.getElementById('empWorkTableNote'), note]]) {
      el.focus();
      el.value = value;
      for (const type of ['input', 'change', 'keyup']) el.dispatchEvent(new Event(type, { bubbles: true }));
      el.blur();
      el.dispatchEvent(new Event('blur', { bubbles: true }));
    }
    await sleep(300);
    const totalRow = label(dlg, '合計')?.closest('tr');
    const total = totalRow && label(totalRow, real) ? real : totalRow?.innerText.replace(/\s+/g, ' ').trim();
    const noteLength = document.getElementById('empWorkTableNote').value.length;
    const ok = time.value === real && total === real && noteLength === note.length;
    if (!ok) return fail(`entry did not take: time ${time.value}, total ${total}, note ${noteLength}/${note.length}`);
    pending = { date, kind: 'works' };
    return { ok, date, job: code, time: real, noteLength };
  });

  // Opens the allowance dialog and ticks every allowance at its default amount. Leaves it open for save().
  const allowance = guarded(async (date) => {
    const why = refuse(date) || (day(date).allowances && 'day already has allowances');
    if (why) return { ok: false, why };
    document.getElementById('allowanceButton' + date).click();
    const dlg = await until(() => dialogs().find((e) => e.innerText.includes('手当登録')));
    if (!dlg) return fail('allowance dialog did not open');
    if (!dlg.innerText.includes(heading(date))) return fail('dialog shows another date');
    const boxes = [...dlg.querySelectorAll('tbody input[type=checkbox]')].filter((c) => c.offsetParent !== null);
    for (const c of boxes) if (!c.checked) c.click();
    await sleep(300);
    const ok = boxes.length > 0 && boxes.every((c) => c.checked);
    if (!ok) return fail(`could not tick allowances: ${boxes.length} found`);
    pending = { date, kind: 'allowances' };
    return { ok, date, ticked: boxes.length };
  });

  const save = guarded(async (date) => {
    const dlg = dialogs()[0];
    if (!dlg) return { ok: false, why: 'no open dialog' };
    if (pending?.date !== date || !dlg.innerText.includes(heading(date))) return fail('the open dialog was not prepared for this date');
    const { kind } = pending;
    pending = null;
    label(dlg, '登録').click();
    if (!(await until(() => !dialogs().length))) return { ok: false, why: 'dialog stayed open' };
    const has = () => {
      const s = day(date);
      return s[kind].length || s[kind] > 0;
    };
    if (await until(has, 5000)) return { ok: true, saved: day(date) };
    return { ok: false, why: `nothing saved in ${kind}`, saved: day(date) };
  });

  const month = () => ({
    yearMonth: data().month.yearMonth,
    days: [...document.querySelectorAll('tr[id^=dateRow]')].map((r) => day(r.id.replace('dateRow', ''))),
  });

  return { month, day, fill, allowance, save, cancel };
})();
'ks ready';
