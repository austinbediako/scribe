export function formatDate(value) {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(value) || Number.isNaN(date.getTime())) return '';
  return date.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

export function formatDateTime(value) {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  return date.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

export function noteTitle(note) {
  return note?.title?.trim() || 'Untitled meeting';
}

export function noteOwner(note) {
  const owner = note?.owner;
  if (!owner) return '';
  if (typeof owner === 'string') return owner;
  return owner.name || owner.email || '';
}

export function noteDate(note) {
  return note?.started_at || note?.created_at || note?.createdAt || note?.date || '';
}

export function noteSummary(note) {
  const raw = note?.summary ?? note?.summary_markdown ?? note?.ai_summary;
  if (!raw) return '';
  if (typeof raw === 'string') return raw;
  if (Array.isArray(raw)) {
    return raw.map((item) => (typeof item === 'string' ? item : item?.text || '')).join('\n');
  }
  if (typeof raw === 'object') {
    if (typeof raw.text === 'string') return raw.text;
    if (typeof raw.markdown === 'string') return raw.markdown;
    return Object.values(raw)
      .map((v) => (typeof v === 'string' ? v : ''))
      .filter(Boolean)
      .join('\n');
  }
  return '';
}

export function summaryPreview(note, max = 160) {
  const text = noteSummary(note) || note.snippet || note.excerpt || '';
  const cleaned = String(text).replace(/\s+/g, ' ').trim();
  return cleaned.length > max ? `${cleaned.slice(0, max)}...` : cleaned;
}

export function normalizeTranscript(transcript) {
  if (!transcript) return [];
  const list = Array.isArray(transcript)
    ? transcript
    : Array.isArray(transcript.segments)
      ? transcript.segments
      : Array.isArray(transcript.utterances)
        ? transcript.utterances
        : [];
  return list.map((item) => {
    if (typeof item === 'string') return { speaker: '', text: item };
    return {
      speaker: item.speaker || item.speaker_name || item.name || '',
      text: item.text || item.content || item.transcript || '',
      timestamp: item.start_time_ms ?? item.start_timestamp ?? item.start ?? item.timestamp ?? null,
      timestampMs: item.start_time_ms ?? null,
    };
  });
}
