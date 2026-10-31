"use client";

import React, { useState } from "react";
import { Image as ImageIcon, ZoomIn, ExternalLink, Clock, Layers } from "lucide-react";
import { VisualEvidenceEntry } from "@/types/investigation";
import { Badge } from "@/components/ui/Badge";
import { Modal } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { getEvidenceAssetUrl } from "@/lib/api";
import { formatDate } from "@/lib/utils";

interface VisualEvidenceGalleryProps {
  entries: VisualEvidenceEntry[];
}

export const VisualEvidenceGallery: React.FC<VisualEvidenceGalleryProps> = ({ entries }) => {
  const [zoomed, setZoomed] = useState<VisualEvidenceEntry | null>(null);

  if (!entries || entries.length === 0) {
    return (
      <div className="p-8 text-center text-xs text-slate-muted border border-dashed border-dark-border rounded-xl">
        No visual evidence retrieved for this investigation.
      </div>
    );
  }

  return (
    <>
      <div className="space-y-4">
        <div className="flex items-center justify-between text-xs text-slate-muted">
          <span className="font-semibold text-slate-text flex items-center gap-1.5">
            <ImageIcon className="h-3.5 w-3.5 text-sky-400" />
            Grafana Dashboards &amp; Screenshots
          </span>
          <span className="font-mono text-[10px]">{entries.length} asset{entries.length !== 1 ? "s" : ""}</span>
        </div>

        <div className="grid grid-cols-1 gap-4">
          {entries.map((entry) => (
            <div
              key={entry.evidence_id}
              className="rounded-xl border border-dark-border bg-dark-surface overflow-hidden shadow-sm"
            >
              {/* Image area */}
              <div
                className="relative aspect-video bg-black/60 cursor-pointer group"
                onClick={() => setZoomed(entry)}
              >
                <img
                  src={getEvidenceAssetUrl(entry.file_id)}
                  alt={entry.title}
                  className="w-full h-full object-cover opacity-90 group-hover:opacity-100 transition-opacity"
                  loading="lazy"
                />
                {/* Hover overlay */}
                <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity">
                  <span className="px-3 py-1.5 rounded-lg bg-dark-surface/90 text-slate-text text-xs font-semibold flex items-center gap-1.5 shadow-lg border border-dark-border">
                    <ZoomIn className="h-3.5 w-3.5 text-accent-primary" />
                    <span>View full size</span>
                  </span>
                </div>
                {/* Evidence ID badge */}
                <div className="absolute top-2 left-2">
                  <Badge
                    variant="outline"
                    size="sm"
                    className="font-mono text-[9px] bg-black/70 border-sky-500/40 text-sky-300"
                  >
                    {entry.evidence_id}
                  </Badge>
                </div>
              </div>

              {/* Metadata */}
              <div className="p-3 space-y-1.5">
                <h4 className="text-xs font-semibold text-slate-text">{entry.title}</h4>
                <p className="text-[11px] text-slate-400 leading-relaxed line-clamp-2">{entry.description}</p>
                <div className="flex items-center gap-3 text-[10px] font-mono text-slate-muted pt-1">
                  {entry.service_id && (
                    <span className="flex items-center gap-1">
                      <Layers className="h-2.5 w-2.5" />
                      {entry.service_id}
                    </span>
                  )}
                  {entry.timestamp && (
                    <span className="flex items-center gap-1">
                      <Clock className="h-2.5 w-2.5" />
                      {formatDate(entry.timestamp)}
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Full-size Zoom Modal */}
      <Modal
        isOpen={!!zoomed}
        onClose={() => setZoomed(null)}
        title={zoomed?.title}
        description={zoomed?.description}
        maxWidth="4xl"
      >
        {zoomed && (
          <div className="space-y-4">
            <div className="rounded-xl overflow-hidden border border-dark-border bg-black max-h-[70vh] flex items-center justify-center">
              <img
                src={getEvidenceAssetUrl(zoomed.file_id)}
                alt={zoomed.title}
                className="w-full h-auto object-contain"
              />
            </div>
            <div className="flex justify-end">
              <Button variant="outline" size="sm" onClick={() => setZoomed(null)}>
                Close
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </>
  );
};

