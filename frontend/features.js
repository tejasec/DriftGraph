/* ================================================================
   DRIFT GRAPH — features.js
   Standalone, dependency-free module implementing:
     1. autoLinkNotes(notes)
     2. detectCommunities(notes,edges)
     3. handleVoiceQuery(query,notes)
     4. handleOCR(text)
   ================================================================ */
(function (global) {
  "use strict";

  const EMBED_DIMS = 384;

  const STOPWORDS = new Set([
    "the","a","an","and","or","to","of","for","in","on","with","is","are",
    "it","this","that","as","by","be","from","its","so","no","not","every",
    "once","each","was","were","has","have","had","but","if","then","than",
    "into","over","under","your","you","can","will","also","new"
  ]);

  function tokenize(text) {
    return String(text || "")
      .toLowerCase()
      .replace(/[#*_`>[\]]/g, " ")
      .split(/[^a-z0-9]+/i)
      .filter((w) => w.length > 2 && !STOPWORDS.has(w));
  }

  function hashString32(str) {
    let hash = 0x811c9dc5;
    for (let i = 0; i < str.length; i++) {
      hash ^= str.charCodeAt(i);
      hash = Math.imul(hash, 0x01000193);
    }
    return hash >>> 0;
  }

  function normalize(vec) {
    let mag = 0;
    for (let i = 0; i < vec.length; i++) mag += vec[i] * vec[i];
    mag = Math.sqrt(mag);
    if (mag === 0) return vec;
    for (let i = 0; i < vec.length; i++) vec[i] /= mag;
    return vec;
  }

  function embedText(text, dims) {
    dims = dims || EMBED_DIMS;
    const vec = new Float32Array(dims);
    const tokens = tokenize(text);
    if (tokens.length === 0) return vec;

    tokens.forEach((token, idx) => {
      const h1 = hashString32(token);
      vec[h1 % dims] += h1 & 1 ? 1 : -1;
      if (idx > 0) {
        const h2 = hashString32(tokens[idx - 1] + "_" + token);
        vec[h2 % dims] += h2 & 1 ? 0.5 : -0.5;
      }
    });

    return normalize(vec);
  }

  function cosineSimilarity(vecA, vecB) {
    let dot = 0, magA = 0, magB = 0;
    const len = Math.min(vecA.length, vecB.length);
    for (let i = 0; i < len; i++) {
      dot += vecA[i] * vecB[i];
      magA += vecA[i] * vecA[i];
      magB += vecB[i] * vecB[i];
    }
    if (magA === 0 || magB === 0) return 0;
    return dot / (Math.sqrt(magA) * Math.sqrt(magB));
  }

  const _embeddingCache = new Map();
  function getNoteEmbedding(note) {
    const text = (note.title || "") + " " + (note.content || "");
    const key = note.id + "::" + hashString32(text);
    if (_embeddingCache.has(key)) return _embeddingCache.get(key);
    const vec = embedText(text);
    _embeddingCache.set(key, vec);
    return vec;
  }

  function autoLinkNotes(notes, options) {
    if (!Array.isArray(notes) || notes.length < 2) return [];
    options = options || {};
    const threshold = options.threshold == null ? 0.7 : options.threshold;

    const embeddings = notes.map((n) => getNoteEmbedding(n));
    const edges = [];

    for (let i = 0; i < notes.length; i++) {
      for (let j = i + 1; j < notes.length; j++) {
        const score = cosineSimilarity(embeddings[i], embeddings[j]);
        if (score > threshold) {
          edges.push([notes[i].id, notes[j].id, +score.toFixed(4)]);
        }
      }
    }

    edges.sort((a, b) => b[2] - a[2]);
    return edges;
  }

  const PALETTE = [
    "#2FD9C4", "#A98CFB", "#F2B84B", "#FB7BA6",
    "#5B8DEF", "#7DD3FC", "#F9A8D4", "#86EFAC"
  ];

  function shuffle(arr) {
    for (let i = arr.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      const tmp = arr[i];
      arr[i] = arr[j];
      arr[j] = tmp;
    }
    return arr;
  }

  function nameCommunity(nodeIds, notes) {
    const counts = new Map();
    nodeIds.forEach((id) => {
      const note = notes.find((n) => n.id === id);
      if (!note) return;
      tokenize(note.title).forEach((w) => counts.set(w, (counts.get(w) || 0) + 1));
    });
    let bestWord = null, bestCount = 0;
    counts.forEach((count, word) => {
      if (count > bestCount) {
        bestCount = count;
        bestWord = word;
      }
    });
    return bestWord;
  }

  function dedupeName(name, existing) {
    if (!(name in existing)) return name;
    let i = 2;
    while (name + "_" + i in existing) i++;
    return name + "_" + i;
  }

  function detectCommunities(notes, edges) {
    if (!Array.isArray(notes) || notes.length === 0) return {};

    const neighbors = new Map();
    notes.forEach((n) => neighbors.set(n.id, []));
    (edges || []).forEach(([a, b, w]) => {
      if (!neighbors.has(a) || !neighbors.has(b)) return;
      neighbors.get(a).push([b, w == null ? 1 : w]);
      neighbors.get(b).push([a, w == null ? 1 : w]);
    });

    const labels = new Map(notes.map((n) => [n.id, n.id]));
    const nodeIds = notes.map((n) => n.id);
    const maxIterations = 8;

    for (let iter = 0; iter < maxIterations; iter++) {
      let changed = false;
      shuffle(nodeIds);
      for (const id of nodeIds) {
        const neigh = neighbors.get(id);
        if (!neigh || neigh.length === 0) continue;

        const tally = new Map();
        neigh.forEach(([otherId, weight]) => {
          const label = labels.get(otherId);
          tally.set(label, (tally.get(label) || 0) + weight);
        });

        let bestLabel = labels.get(id), bestScore = -Infinity;
        tally.forEach((score, label) => {
          if (score > bestScore) {
            bestScore = score;
            bestLabel = label;
          }
        });

        if (bestLabel !== labels.get(id)) {
          labels.set(id, bestLabel);
          changed = true;
        }
      }
      if (!changed) break;
    }

    const groups = new Map();
    labels.forEach((label, id) => {
      if (!groups.has(label)) groups.set(label, []);
      groups.get(label).push(id);
    });

    const result = {};
    let colorIdx = 0;
    groups.forEach((memberIds) => {
      const name = nameCommunity(memberIds, notes) || "community_" + (colorIdx + 1);
      result[dedupeName(name, result)] = {
        nodes: memberIds,
        color: PALETTE[colorIdx % PALETTE.length]
      };
      colorIdx++;
    });

    return result;
  }

  function simulateTranscription(query) {
    return String(query || "").trim().replace(/\s+/g, " ");
  }

  function extractSnippet(content, maxLen) {
    maxLen = maxLen || 160;
    const plain = String(content || "")
      .replace(/^#+\s*/gm, "")
      .replace(/\*\*(.+?)\*\*/g, "$1")
      .replace(/\*(.+?)\*/g, "$1")
      .replace(/\n+/g, " ")
      .trim();
    if (plain.length <= maxLen) return plain;
    const cut = plain.slice(0, maxLen);
    const lastSpace = cut.lastIndexOf(" ");
    return cut.slice(0, lastSpace > 0 ? lastSpace : maxLen) + "…";
  }

  function handleVoiceQuery(query, notes) {
    const transcript = simulateTranscription(query);

    if (!Array.isArray(notes) || notes.length === 0) {
      return {
        answer: "No notes in the graph yet — add some notes first.",
        sourceNoteId: null,
        transcript
      };
    }

    const queryVec = embedText(transcript);
    let best = null, bestScore = -Infinity;
    notes.forEach((n) => {
      const score = cosineSimilarity(queryVec, getNoteEmbedding(n));
      if (score > bestScore) {
        bestScore = score;
        best = n;
      }
    });

    if (!best || bestScore < 0.15) {
      return {
        answer: "I couldn't find a close match in your notes for that — try rephrasing or asking about a specific topic.",
        sourceNoteId: null,
        transcript,
        confidence: +Math.max(0, bestScore).toFixed(2)
      };
    }

    return {
      answer: 'From "' + best.title + '": ' + extractSnippet(best.content),
      sourceNoteId: best.id,
      transcript,
      confidence: +bestScore.toFixed(2)
    };
  }

  let _ocrCounter = 0;

  function deriveTitle(text) {
    if (!text) return "";
    const firstLine = text.split("\n")[0].trim();
    const words = firstLine.split(/\s+/).slice(0, 8).join(" ");
    return words.length < firstLine.length ? words + "…" : words;
  }

  function handleOCR(text, options) {
    options = options || {};
    const cleanText = String(text || "").trim();
    _ocrCounter++;

    const id = options.idPrefix
      ? options.idPrefix + _ocrCounter
      : "ocr" + Date.now().toString(36) + _ocrCounter;

    const title = deriveTitle(cleanText) || "OCR note " + _ocrCounter;

    return {
      id,
      title,
      community: options.community || null,
      content: "# " + title + "\n\n" + cleanText,
      source: "ocr",
      createdAt: new Date().toISOString()
    };
  }

  const DriftFeatures = {
    autoLinkNotes,
    detectCommunities,
    handleVoiceQuery,
    handleOCR,
    embedText,
    cosineSimilarity
  };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = DriftFeatures;
  }
  global.DriftFeatures = DriftFeatures;
})(typeof window !== "undefined" ? window : globalThis);
