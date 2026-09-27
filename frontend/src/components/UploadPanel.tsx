import { useState } from "react";
import type { UploadProfile } from "../services/api";

interface Props {
  busy: boolean;
  error: string;
  profiles: UploadProfile[];
  onPick: (file: File, profile: string) => void;
}

const ERROR_LIMIT = 320;
const FALLBACK: UploadProfile[] = [{ id: "generic", label: "Generic (native P041 schema)" }];

/**
 * CSV ingestion. The profile is chosen explicitly because the backend rejects a
 * file that does not fit the chosen profile rather than silently mapping it onto
 * invented values.
 */
export default function UploadPanel({ busy, error, profiles, onPick }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [profile, setProfile] = useState("generic");
  const options = profiles.length > 0 ? profiles : FALLBACK;

  return (
    <div className="panel">
      <div className="panel-head">
        <h3 className="panel-title">Ingest plant telemetry</h3>
        <span className="panel-note">CSV · max 5 MB · not stored</span>
      </div>
      <p className="panel-note" style={{ margin: "0 0 0.8rem" }}>
        Choose the profile that matches the file&apos;s columns. A file that does not fit the
        chosen profile is rejected rather than mapped onto invented values, and any field the
        source does not measure is reported as derived.
      </p>

      <div className="toolbar" style={{ marginBottom: "0.8rem" }}>
        <label className="field">
          <span className="field-label">Dataset profile</span>
          <select value={profile} onChange={(e) => setProfile(e.target.value)}>
            {options.map((p) => (
              <option key={p.id} value={p.id}>
                {p.label}
              </option>
            ))}
          </select>
        </label>
        <label className="field" style={{ flex: "1 1 16rem" }}>
          <span className="field-label">Choose CSV</span>
          <input
            type="file"
            accept=".csv,text/csv"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
        </label>
        <button
          className="btn btn-primary"
          disabled={!file || busy}
          onClick={() => file && onPick(file, profile)}
        >
          {busy ? "Analysing…" : "Upload & analyse"}
        </button>
      </div>

      {error && (
        <div className="callout callout-error" role="alert">
          {error.length > ERROR_LIMIT ? `${error.slice(0, ERROR_LIMIT)}…` : error}
        </div>
      )}
    </div>
  );
}
