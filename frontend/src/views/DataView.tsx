import UploadPanel from "../components/UploadPanel";
import type { UploadProfile } from "../services/api";
import type { DemoParams } from "../services/api";

interface Props {
  params: DemoParams;
  onParams: (p: DemoParams) => void;
  profiles: UploadProfile[];
  uploadBusy: boolean;
  uploadError: string;
  lastResult: {
    filename: string;
    profile: string;
    csv_rows: number;
    observation_count: number;
    derived: string[];
  } | null;
  onUpload: (file: File, profile: string) => void;
}

/** Secondary workflow: bring your own CSV, or re-run the simulator. */
export default function DataView({
  params,
  onParams,
  profiles,
  uploadBusy,
  uploadError,
  lastResult,
  onUpload,
}: Props) {
  return (
    <>
      <header className="view-head">
        <div>
          <h1 className="view-title">Data ingestion</h1>
          <p className="view-sub">
            Analyse your own plant CSV, or re-run the deterministic simulator with different
            parameters
          </p>
        </div>
      </header>

      <div className="grid-12">
        <div className="col-7">
          <UploadPanel
            busy={uploadBusy}
            error={uploadError}
            profiles={profiles}
            onPick={onUpload}
          />
          {lastResult && (
            <div className="panel" style={{ marginTop: "1rem" }}>
              <div className="panel-head">
                <h3 className="panel-title">Last ingest</h3>
                <span className="panel-note">{lastResult.filename}</span>
              </div>
              <div className="metrics-2">
                <div className="metric-cell">
                  <div className="metric-label">CSV rows</div>
                  <div className="metric-value">{lastResult.csv_rows.toLocaleString()}</div>
                </div>
                <div className="metric-cell">
                  <div className="metric-label">Observations</div>
                  <div className="metric-value">{lastResult.observation_count.toLocaleString()}</div>
                </div>
              </div>
              <div style={{ marginTop: "0.7rem" }}>
                <div className="kpi-label">Profile</div>
                <p className="mono" style={{ margin: "0.2rem 0 0", fontSize: "0.85rem" }}>
                  {lastResult.profile}
                </p>
              </div>
              <div style={{ marginTop: "0.7rem" }}>
                <div className="kpi-label">Derived fields ({lastResult.derived.length})</div>
                {lastResult.derived.length === 0 ? (
                  <p className="panel-note" style={{ marginTop: "0.2rem" }}>
                    None — every field was measured in the source file.
                  </p>
                ) : (
                  <ul className="doc-ul" style={{ marginTop: "0.2rem" }}>
                    {lastResult.derived.map((d) => (
                      <li key={d} className="doc-li" style={{ fontSize: "0.84rem" }}>
                        {d}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          )}
        </div>

        <div className="col-5">
          <div className="panel">
            <div className="panel-head">
              <h3 className="panel-title">Simulator</h3>
              <span className="panel-note">Deterministic from the seed</span>
            </div>
            <div className="toolbar">
              <label className="field">
                <span className="field-label">Machines</span>
                <select
                  value={params.machines}
                  onChange={(e) => onParams({ ...params, machines: Number(e.target.value) })}
                >
                  {[2, 3, 4, 6, 8].map((n) => (
                    <option key={n} value={n}>{n}</option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span className="field-label">Observations</span>
                <select
                  value={params.observations}
                  onChange={(e) => onParams({ ...params, observations: Number(e.target.value) })}
                >
                  {[24, 48, 72, 96].map((n) => (
                    <option key={n} value={n}>{n}</option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span className="field-label">Seed</span>
                <input
                  type="number"
                  value={params.seed}
                  min={0}
                  onChange={(e) => onParams({ ...params, seed: Number(e.target.value) })}
                />
              </label>
            </div>
            <p className="panel-note" style={{ marginTop: "0.7rem" }}>
              Changing any parameter reloads every panel from the backend. The same seed always
              produces the same dataset, so figures stay reproducible between runs.
            </p>
          </div>

          <div className="panel" style={{ marginTop: "1rem" }}>
            <div className="panel-head">
              <h3 className="panel-title">Available profiles</h3>
            </div>
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Profile</th>
                    <th>Dataset</th>
                  </tr>
                </thead>
                <tbody>
                  {profiles.map((p) => (
                    <tr key={p.id}>
                      <td className="mono">{p.id}</td>
                      <td style={{ whiteSpace: "normal" }}>{p.label}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="panel-note" style={{ marginTop: "0.6rem" }}>
              A file that does not fit the selected profile is rejected with the missing columns
              rather than mapped onto zero values.
            </p>
          </div>
        </div>
      </div>
    </>
  );
}
