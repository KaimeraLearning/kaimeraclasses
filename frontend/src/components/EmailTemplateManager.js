import React, { useEffect, useState } from 'react';
import { Mail, Save, RotateCcw, Send, Upload, Image as ImageIcon, Paperclip, X, Trash2 } from 'lucide-react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Textarea } from './ui/textarea';
import { toast } from 'sonner';
import { API, apiFetch, getApiError } from '../utils/api';

/**
 * Admin-facing Email Template editor.
 *  - Lists every email event the platform fires
 *  - Lets admin override subject / title / intro / body_html / cta on each
 *  - Live preview pane renders the resulting HTML with {{var}} sample fills
 *  - Media library (images + files) — attach a logo (inline) and any number of files
 *  - "Send test" delivers the rendered email to admin's inbox
 *  - "Reset to default" deletes the override
 */
export default function EmailTemplateManager() {
  const [events, setEvents] = useState([]);
  const [media, setMedia] = useState([]);
  const [selectedKey, setSelectedKey] = useState('');
  const [busy, setBusy] = useState(false);

  // editable fields
  const [subject, setSubject] = useState('');
  const [title, setTitle] = useState('');
  const [intro, setIntro] = useState('');
  const [bodyHtml, setBodyHtml] = useState('');
  const [ctaLabel, setCtaLabel] = useState('');
  const [ctaUrl, setCtaUrl] = useState('');
  const [inlineImageId, setInlineImageId] = useState('');
  const [attachmentIds, setAttachmentIds] = useState([]);

  // test send
  const [testTo, setTestTo] = useState('');

  const loadEvents = async () => {
    try {
      const r = await apiFetch(`${API}/admin/email-events`, { credentials: 'include' });
      const data = await r.json();
      setEvents(Array.isArray(data) ? data : []);
      if (Array.isArray(data) && data.length && !selectedKey) selectEvent(data[0]);
    } catch (e) {
      toast.error('Failed to load events');
    }
  };

  const loadMedia = async () => {
    try {
      const r = await apiFetch(`${API}/admin/email-media`, { credentials: 'include' });
      const data = await r.json();
      setMedia(Array.isArray(data) ? data : []);
    } catch (e) {
      // silent
    }
  };

  useEffect(() => { loadEvents(); loadMedia(); /* eslint-disable-next-line */ }, []);

  const selectEvent = (ev) => {
    setSelectedKey(ev.event_key);
    const src = (ev.is_overridden && ev.override) ? ev.override : ev.default;
    setSubject(src.subject || '');
    setTitle(src.title || '');
    setIntro(src.intro || '');
    setBodyHtml(src.body_html || '');
    setCtaLabel(src.cta_label || '');
    setCtaUrl(src.cta_url || '');
    setInlineImageId(ev.inline_image_id || '');
    setAttachmentIds(ev.attachment_ids || []);
  };

  const currentEvent = events.find(e => e.event_key === selectedKey);

  const onSelectChange = (key) => {
    const ev = events.find(e => e.event_key === key);
    if (ev) selectEvent(ev);
  };

  const save = async () => {
    if (!selectedKey) return;
    setBusy(true);
    try {
      const r = await apiFetch(`${API}/admin/email-templates/${selectedKey}`, {
        method: 'PUT',
        credentials: 'include',
        body: JSON.stringify({
          subject, title, intro, body_html: bodyHtml,
          cta_label: ctaLabel, cta_url: ctaUrl,
          inline_image_id: inlineImageId || null,
          attachment_ids: attachmentIds,
        }),
      });
      if (!r.ok) throw new Error(await getApiError(r));
      toast.success('Template saved');
      await loadEvents();
    } catch (e) {
      toast.error(e.message || 'Save failed');
    } finally { setBusy(false); }
  };

  const reset = async () => {
    if (!selectedKey) return;
    if (!window.confirm('Restore the default template? Your changes for this event will be lost.')) return;
    setBusy(true);
    try {
      const r = await apiFetch(`${API}/admin/email-templates/${selectedKey}`, {
        method: 'DELETE', credentials: 'include',
      });
      if (!r.ok) throw new Error(await getApiError(r));
      toast.success('Reset to default');
      await loadEvents();
      // re-select to refresh editor with defaults
      const refreshed = await (await apiFetch(`${API}/admin/email-events`, { credentials: 'include' })).json();
      const ev = (refreshed || []).find(e => e.event_key === selectedKey);
      if (ev) selectEvent(ev);
    } catch (e) {
      toast.error(e.message || 'Reset failed');
    } finally { setBusy(false); }
  };

  const sendTest = async () => {
    if (!selectedKey) return;
    const to = testTo.trim();
    if (!to) { toast.error('Enter a recipient email'); return; }
    setBusy(true);
    try {
      const r = await apiFetch(`${API}/admin/email-templates/${selectedKey}/test`, {
        method: 'POST', credentials: 'include',
        body: JSON.stringify({ to }),
      });
      if (!r.ok) throw new Error(await getApiError(r));
      const data = await r.json();
      if (data.ok === false) {
        toast.error(`SMTP rejected: ${data.error}`, { duration: 8000 });
      } else {
        toast.success(data.message || 'Test sent — check your inbox');
      }
    } catch (e) {
      toast.error(e.message || 'Test failed');
    } finally { setBusy(false); }
  };

  const uploadMedia = async (e, kind) => {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = ''; // reset so same file can be re-picked
    const fd = new FormData();
    fd.append('file', file);
    fd.append('kind', kind);
    setBusy(true);
    try {
      const r = await apiFetch(`${API}/admin/email-media`, {
        method: 'POST', credentials: 'include', body: fd,
      });
      if (!r.ok) throw new Error(await getApiError(r));
      toast.success('Uploaded');
      await loadMedia();
    } catch (err) {
      toast.error(err.message || 'Upload failed');
    } finally { setBusy(false); }
  };

  const deleteMedia = async (mid) => {
    if (!window.confirm('Delete this media? Templates using it must detach first.')) return;
    setBusy(true);
    try {
      const r = await apiFetch(`${API}/admin/email-media/${mid}`, {
        method: 'DELETE', credentials: 'include',
      });
      if (!r.ok) throw new Error(await getApiError(r));
      toast.success('Deleted');
      await loadMedia();
    } catch (e) {
      toast.error(e.message || 'Delete failed');
    } finally { setBusy(false); }
  };

  // ── live preview rendering: substitute {{var}} with [var] sample, then wrap with branded HTML
  const sampleFill = (txt) => {
    if (!txt) return '';
    return txt.replace(/\{\{\s*([a-zA-Z0-9_]+)\s*\}\}/g, (_, k) => `<span style="background:#fef3c7;padding:1px 6px;border-radius:4px;color:#92400e;font-weight:600;">[${k}]</span>`);
  };
  const previewLogo = inlineImageId ? media.find(m => m.media_id === inlineImageId) : null;
  const previewHtml = `<div style="font-family:Arial,sans-serif;max-width:520px;margin:0 auto;padding:32px 24px;background:#f8fafc;border-radius:16px;">
    ${previewLogo ? `<div style="text-align:center;margin:0 0 16px;"><img src="${API}/admin/email-media/file/${previewLogo.media_id}" alt="Logo" style="max-width:160px;max-height:80px;"/></div>` : ''}
    <h2 style="color:#0ea5e9;margin:0 0 8px;">${sampleFill(title)}</h2>
    <p style="color:#475569;margin:0 0 16px;">${sampleFill(intro)}</p>
    ${sampleFill(bodyHtml)}
    ${(ctaLabel && ctaUrl) ? `<div style="text-align:center;margin:24px 0;"><a href="${ctaUrl}" style="display:inline-block;padding:12px 28px;background:#0ea5e9;color:#fff;border-radius:24px;text-decoration:none;font-weight:bold;">${sampleFill(ctaLabel)}</a></div>` : ''}
    <p style="color:#94a3b8;font-size:12px;margin-top:24px;">Kaimera Learning · This is an automated email · Please do not reply.</p>
  </div>`;

  const imageMedia = media.filter(m => m.kind === 'image');
  const fileMedia = media.filter(m => m.kind === 'file');

  return (
    <div className="bg-white rounded-3xl border-2 border-slate-100 p-6 col-span-1 lg:col-span-2" data-testid="email-template-manager">
      <h3 className="font-semibold text-slate-800 mb-4 flex items-center gap-2">
        <Mail className="w-5 h-5 text-sky-500" /> Email Template Editor
      </h3>
      <p className="text-xs text-slate-500 mb-4">
        Customize the content of every transactional email Kaimera sends. Changes apply instantly — no redeploy needed.
        Use <code className="bg-slate-100 px-1 rounded">{`{{variable}}`}</code> placeholders; they are replaced with real data when the email fires.
      </p>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* ── LEFT: Editor ─────────────────────────────────────── */}
        <div className="space-y-3">
          <div>
            <Label className="text-xs">Email Trigger</Label>
            <select
              className="w-full rounded-xl border-2 border-slate-200 px-3 py-2 text-sm"
              value={selectedKey}
              onChange={e => onSelectChange(e.target.value)}
              data-testid="email-template-select"
            >
              {events.map(ev => (
                <option key={ev.event_key} value={ev.event_key}>
                  {ev.is_overridden ? '✎ ' : ''}{ev.name}
                </option>
              ))}
            </select>
            {currentEvent && (
              <p className="text-[11px] text-slate-500 mt-1">{currentEvent.description}</p>
            )}
            {currentEvent?.variables?.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1">
                <span className="text-[10px] text-slate-400 self-center">Available:</span>
                {currentEvent.variables.map(v => (
                  <code key={v} className="text-[10px] bg-amber-50 text-amber-700 px-1.5 py-0.5 rounded border border-amber-200">{`{{${v}}}`}</code>
                ))}
              </div>
            )}
          </div>

          <div>
            <Label className="text-xs">Subject</Label>
            <Input value={subject} onChange={e => setSubject(e.target.value)} className="rounded-xl" data-testid="email-template-subject" />
          </div>
          <div>
            <Label className="text-xs">Title (heading at top of email)</Label>
            <Input value={title} onChange={e => setTitle(e.target.value)} className="rounded-xl" data-testid="email-template-title" />
          </div>
          <div>
            <Label className="text-xs">Intro paragraph</Label>
            <Textarea rows={3} value={intro} onChange={e => setIntro(e.target.value)} className="rounded-xl text-sm" data-testid="email-template-intro" />
          </div>
          <div>
            <Label className="text-xs">Body HTML (optional, for rich content like credentials block)</Label>
            <Textarea rows={5} value={bodyHtml} onChange={e => setBodyHtml(e.target.value)} className="rounded-xl text-xs font-mono" data-testid="email-template-body" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label className="text-xs">CTA Button Label</Label>
              <Input value={ctaLabel} onChange={e => setCtaLabel(e.target.value)} className="rounded-xl" data-testid="email-template-cta-label" />
            </div>
            <div>
              <Label className="text-xs">CTA Button URL</Label>
              <Input value={ctaUrl} onChange={e => setCtaUrl(e.target.value)} className="rounded-xl" data-testid="email-template-cta-url" />
            </div>
          </div>

          {/* Inline Logo */}
          <div className="border-t border-slate-100 pt-3">
            <Label className="text-xs flex items-center gap-1 mb-2"><ImageIcon className="w-3.5 h-3.5" /> Inline Logo (shown at top of email)</Label>
            <div className="flex flex-wrap gap-2 items-center">
              <select
                className="rounded-xl border-2 border-slate-200 px-2 py-1 text-xs flex-1 min-w-[140px]"
                value={inlineImageId}
                onChange={e => setInlineImageId(e.target.value)}
                data-testid="email-template-inline-select"
              >
                <option value="">— None —</option>
                {imageMedia.map(m => <option key={m.media_id} value={m.media_id}>{m.filename}</option>)}
              </select>
              <label className="cursor-pointer text-xs bg-slate-100 hover:bg-slate-200 rounded-full px-3 py-1.5 flex items-center gap-1" data-testid="email-template-upload-image">
                <Upload className="w-3 h-3" /> Upload
                <input type="file" accept="image/*" className="hidden" onChange={e => uploadMedia(e, 'image')} />
              </label>
            </div>
          </div>

          {/* Attachments */}
          <div>
            <Label className="text-xs flex items-center gap-1 mb-2"><Paperclip className="w-3.5 h-3.5" /> File Attachments (downloadable)</Label>
            <div className="space-y-1 mb-2">
              {attachmentIds.map(aid => {
                const m = media.find(x => x.media_id === aid);
                return (
                  <div key={aid} className="flex items-center justify-between bg-slate-50 rounded-lg px-2 py-1 text-xs">
                    <span className="truncate">{m?.filename || aid}</span>
                    <button onClick={() => setAttachmentIds(attachmentIds.filter(x => x !== aid))} className="text-rose-500 hover:text-rose-600" data-testid={`detach-${aid}`}>
                      <X className="w-3 h-3" />
                    </button>
                  </div>
                );
              })}
            </div>
            <div className="flex gap-2 items-center">
              <select
                className="rounded-xl border-2 border-slate-200 px-2 py-1 text-xs flex-1"
                onChange={e => {
                  const v = e.target.value;
                  if (v && !attachmentIds.includes(v)) setAttachmentIds([...attachmentIds, v]);
                  e.target.value = '';
                }}
                data-testid="email-template-attach-select"
              >
                <option value="">+ Attach from library…</option>
                {fileMedia.filter(m => !attachmentIds.includes(m.media_id)).map(m => (
                  <option key={m.media_id} value={m.media_id}>{m.filename}</option>
                ))}
              </select>
              <label className="cursor-pointer text-xs bg-slate-100 hover:bg-slate-200 rounded-full px-3 py-1.5 flex items-center gap-1" data-testid="email-template-upload-file">
                <Upload className="w-3 h-3" /> Upload
                <input type="file" className="hidden" onChange={e => uploadMedia(e, 'file')} />
              </label>
            </div>
          </div>

          <div className="flex flex-wrap gap-2 pt-2 border-t border-slate-100">
            <Button onClick={save} disabled={busy || !selectedKey} className="bg-rose-500 hover:bg-rose-600 text-white rounded-full" data-testid="email-template-save">
              <Save className="w-4 h-4 mr-1" /> Save
            </Button>
            <Button onClick={reset} disabled={busy || !currentEvent?.is_overridden} variant="outline" className="rounded-full text-xs" data-testid="email-template-reset">
              <RotateCcw className="w-3.5 h-3.5 mr-1" /> Reset to default
            </Button>
            <div className="flex gap-1 ml-auto items-center">
              <Input value={testTo} onChange={e => setTestTo(e.target.value)} placeholder="test@email.com" className="rounded-xl h-8 text-xs w-44" data-testid="email-template-test-to" />
              <Button onClick={sendTest} disabled={busy || !selectedKey} variant="outline" className="rounded-full text-xs" data-testid="email-template-test-send">
                <Send className="w-3.5 h-3.5 mr-1" /> Send test
              </Button>
            </div>
          </div>
        </div>

        {/* ── RIGHT: Live preview + Media Library ─────────────── */}
        <div className="space-y-4">
          <div>
            <Label className="text-xs mb-2 block">Live Preview</Label>
            <div className="bg-slate-50 rounded-xl border border-slate-200 p-3 max-h-[480px] overflow-auto" data-testid="email-template-preview">
              <div dangerouslySetInnerHTML={{ __html: previewHtml }} />
            </div>
          </div>

          <div className="border-t border-slate-100 pt-3">
            <Label className="text-xs mb-2 block">Media Library ({media.length})</Label>
            <div className="max-h-40 overflow-y-auto space-y-1" data-testid="email-template-media-list">
              {media.length === 0 && (
                <p className="text-xs text-slate-400 italic">No media uploaded yet.</p>
              )}
              {media.map(m => (
                <div key={m.media_id} className="flex items-center justify-between bg-slate-50 rounded-lg px-2 py-1 text-xs">
                  <div className="flex items-center gap-2 min-w-0">
                    {m.kind === 'image'
                      ? <ImageIcon className="w-3.5 h-3.5 text-emerald-500 flex-shrink-0" />
                      : <Paperclip className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />}
                    <span className="truncate">{m.filename}</span>
                    <span className="text-[10px] text-slate-400 flex-shrink-0">{(m.size / 1024).toFixed(1)}KB</span>
                  </div>
                  <button onClick={() => deleteMedia(m.media_id)} className="text-rose-500 hover:text-rose-600 ml-2" data-testid={`media-delete-${m.media_id}`}>
                    <Trash2 className="w-3 h-3" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
