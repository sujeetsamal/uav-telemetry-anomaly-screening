import React from 'react';
import { Award } from 'lucide-react';
import { MethodEvaluation } from '../types/telemetry';

interface EvaluationTableProps {
  evaluations: MethodEvaluation[];
  loading: boolean;
}

export const EvaluationTable: React.FC<EvaluationTableProps> = ({ evaluations, loading }) => {
  if (loading) {
    return (
      <div className="bg-gray-900/60 border border-gray-800 rounded-2xl p-5 animate-pulse">
        <div className="h-40 bg-gray-800/50 rounded-xl"></div>
      </div>
    );
  }

  if (!evaluations || evaluations.length === 0) {
    return (
      <div className="bg-gray-900/60 border border-gray-800/80 rounded-2xl p-6 text-center text-gray-400 text-xs font-mono">
        No ground-truth benchmark metrics available for custom uploaded logs without labels. Load simulated 15-min flight to view evaluation.
      </div>
    );
  }

  return (
    <div className="bg-gray-900/60 border border-gray-800/80 rounded-2xl p-4">
      <div className="flex items-center justify-between border-b border-gray-800 pb-3 mb-3">
        <div className="flex items-center gap-2">
          <Award className="w-4 h-4 text-amber-400" />
          <h3 className="text-sm font-semibold text-gray-200 uppercase tracking-wider">
            Benchmark Method Comparison (Ground-Truth Validation)
          </h3>
        </div>
        <div className="text-[11px] font-mono text-gray-400">
          Ranked by F1-Score on 8 Seeded Ground-Truth Anomalies
        </div>
      </div>

      <div className="overflow-x-auto rounded-xl border border-gray-800/80 bg-gray-950/50">
        <table className="w-full text-left text-xs font-mono">
          <thead className="bg-gray-900/90 text-gray-400 uppercase tracking-wider border-b border-gray-800">
            <tr>
              <th className="py-2.5 px-3">Detector Method</th>
              <th className="py-2.5 px-3">Precision</th>
              <th className="py-2.5 px-3">Recall</th>
              <th className="py-2.5 px-3">F1-Score</th>
              <th className="py-2.5 px-3">Detection Delay</th>
              <th className="py-2.5 px-3">Event Recall</th>
              <th className="py-2.5 px-3">TP</th>
              <th className="py-2.5 px-3">FP</th>
              <th className="py-2.5 px-3">FN</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-800/60">
            {evaluations.map((ev, idx) => {
              const isTop = idx === 0;
              return (
                <tr
                  key={ev.method}
                  className={`transition-colors ${
                    isTop ? 'bg-cyan-950/30 font-semibold' : 'hover:bg-gray-900/60'
                  }`}
                >
                  <td className="py-2.5 px-3 flex items-center gap-2">
                    {isTop ? (
                      <span className="w-2 h-2 rounded-full bg-cyan-400"></span>
                    ) : (
                      <span className="w-2 h-2 rounded-full bg-gray-600"></span>
                    )}
                    <span className={isTop ? 'text-cyan-300' : 'text-gray-200'}>{ev.method}</span>
                    {isTop && (
                      <span className="px-1.5 py-0.2 bg-cyan-500/20 text-cyan-300 text-[10px] rounded border border-cyan-500/40">
                        TOP
                      </span>
                    )}
                  </td>
                  <td className="py-2.5 px-3 text-gray-300">{(ev.precision * 100).toFixed(1)}%</td>
                  <td className="py-2.5 px-3 text-gray-300">{(ev.recall * 100).toFixed(1)}%</td>
                  <td className="py-2.5 px-3">
                    <span
                      className={`px-2 py-0.5 rounded text-[11px] font-bold ${
                        ev.f1_score >= 0.35
                          ? 'bg-emerald-950/80 text-emerald-300 border border-emerald-800/60'
                          : ev.f1_score >= 0.20
                          ? 'bg-amber-950/80 text-amber-300 border border-amber-800/60'
                          : 'bg-gray-800 text-gray-300 border border-gray-700'
                      }`}
                    >
                      {ev.f1_score.toFixed(3)}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 text-gray-300">{ev.detection_delay_s.toFixed(2)}s</td>
                  <td className="py-2.5 px-3 text-emerald-400 font-semibold">
                    {(ev.event_recall * 100).toFixed(0)}%
                  </td>
                  <td className="py-2.5 px-3 text-emerald-400">{ev.tp}</td>
                  <td className="py-2.5 px-3 text-rose-400">{ev.fp}</td>
                  <td className="py-2.5 px-3 text-amber-400">{ev.fn}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
