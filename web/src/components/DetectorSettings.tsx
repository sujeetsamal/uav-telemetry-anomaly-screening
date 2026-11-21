import React, { useState } from 'react';
import { RefreshCw, Sliders, Sparkles } from 'lucide-react';
import { DetectorParameters } from '../types/telemetry';

interface DetectorSettingsProps {
  onApply: (params: DetectorParameters) => Promise<void>;
  loading: boolean;
}

export const DetectorSettings: React.FC<DetectorSettingsProps> = ({ onApply, loading }) => {
  const [params, setParams] = useState<DetectorParameters>({
    zscore_thresh: 3.2,
    iqr_k: 2.5,
    ewma_mult: 3.0,
    iso_contamination: 0.08,
    ensemble_thresh: 0.35,
  });

  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await onApply(params);
    } finally {
      setSaving(false);
    }
  };

  const handleReset = () => {
    setParams({
      zscore_thresh: 3.2,
      iqr_k: 2.5,
      ewma_mult: 3.0,
      iso_contamination: 0.08,
      ensemble_thresh: 0.35,
    });
  };

  return (
    <div className="bg-gray-900/60 border border-gray-800/80 rounded-2xl p-4">
      <div className="flex items-center justify-between border-b border-gray-800 pb-3 mb-4">
        <div className="flex items-center gap-2">
          <Sliders className="w-4 h-4 text-cyan-400" />
          <h3 className="text-sm font-semibold text-gray-200 uppercase tracking-wider">
            Detector Sensitivity & Ensemble Tuning
          </h3>
        </div>
        <button
          type="button"
          onClick={handleReset}
          className="text-xs text-gray-400 hover:text-gray-200 flex items-center gap-1 font-mono transition-colors"
        >
          <RefreshCw className="w-3 h-3" /> Reset Defaults
        </button>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          {/* Z-score threshold */}
          <div className="bg-gray-950 p-3 rounded-xl border border-gray-800/80">
            <div className="flex items-center justify-between text-xs font-mono text-gray-400 mb-1">
              <span>Z-Score Threshold (σ)</span>
              <span className="text-cyan-400 font-bold">{params.zscore_thresh.toFixed(1)}</span>
            </div>
            <input
              type="range"
              min="1.5"
              max="5.0"
              step="0.1"
              value={params.zscore_thresh}
              onChange={(e) => setParams({ ...params, zscore_thresh: parseFloat(e.target.value) })}
              className="w-full accent-cyan-400 h-1.5 bg-gray-800 rounded-lg cursor-pointer"
            />
            <span className="text-[10px] text-gray-400 mt-1 block">Higher = less sensitive</span>
          </div>

          {/* IQR Factor */}
          <div className="bg-gray-950 p-3 rounded-xl border border-gray-800/80">
            <div className="flex items-center justify-between text-xs font-mono text-gray-400 mb-1">
              <span>IQR Multiplier (k)</span>
              <span className="text-cyan-400 font-bold">{params.iqr_k.toFixed(1)}</span>
            </div>
            <input
              type="range"
              min="1.0"
              max="4.0"
              step="0.1"
              value={params.iqr_k}
              onChange={(e) => setParams({ ...params, iqr_k: parseFloat(e.target.value) })}
              className="w-full accent-cyan-400 h-1.5 bg-gray-800 rounded-lg cursor-pointer"
            />
            <span className="text-[10px] text-gray-400 mt-1 block">Tukey residual cutoff</span>
          </div>

          {/* EWMA Multiplier */}
          <div className="bg-gray-950 p-3 rounded-xl border border-gray-800/80">
            <div className="flex items-center justify-between text-xs font-mono text-gray-400 mb-1">
              <span>EWMA Control (L)</span>
              <span className="text-cyan-400 font-bold">{params.ewma_mult.toFixed(1)}</span>
            </div>
            <input
              type="range"
              min="1.5"
              max="4.5"
              step="0.1"
              value={params.ewma_mult}
              onChange={(e) => setParams({ ...params, ewma_mult: parseFloat(e.target.value) })}
              className="w-full accent-cyan-400 h-1.5 bg-gray-800 rounded-lg cursor-pointer"
            />
            <span className="text-[10px] text-gray-400 mt-1 block">Moving average control limit</span>
          </div>

          {/* Isolation Forest Contamination */}
          <div className="bg-gray-950 p-3 rounded-xl border border-gray-800/80">
            <div className="flex items-center justify-between text-xs font-mono text-gray-400 mb-1">
              <span>IForest Outlier Ratio</span>
              <span className="text-cyan-400 font-bold">{(params.iso_contamination * 100).toFixed(0)}%</span>
            </div>
            <input
              type="range"
              min="0.02"
              max="0.20"
              step="0.01"
              value={params.iso_contamination}
              onChange={(e) => setParams({ ...params, iso_contamination: parseFloat(e.target.value) })}
              className="w-full accent-cyan-400 h-1.5 bg-gray-800 rounded-lg cursor-pointer"
            />
            <span className="text-[10px] text-gray-400 mt-1 block">Expected anomaly fraction</span>
          </div>

          {/* Ensemble Consensus Threshold */}
          <div className="bg-gray-950 p-3 rounded-xl border border-gray-800/80">
            <div className="flex items-center justify-between text-xs font-mono text-gray-400 mb-1">
              <span>Ensemble Consensus</span>
              <span className="text-cyan-400 font-bold">{params.ensemble_thresh.toFixed(2)}</span>
            </div>
            <input
              type="range"
              min="0.15"
              max="0.70"
              step="0.05"
              value={params.ensemble_thresh}
              onChange={(e) => setParams({ ...params, ensemble_thresh: parseFloat(e.target.value) })}
              className="w-full accent-cyan-400 h-1.5 bg-gray-800 rounded-lg cursor-pointer"
            />
            <span className="text-[10px] text-gray-400 mt-1 block">Weighted vote trigger</span>
          </div>
        </div>

        <div className="flex justify-end pt-1">
          <button
            type="submit"
            disabled={saving || loading}
            className="px-5 py-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 text-white font-semibold text-xs flex items-center gap-2 hover:from-cyan-400 hover:to-blue-500 shadow-lg shadow-cyan-500/20 disabled:opacity-50 transition-all font-mono"
          >
            <Sparkles className="w-3.5 h-3.5" />
            {saving ? 'Re-Screening Telemetry...' : 'Apply & Run Screening'}
          </button>
        </div>
      </form>
    </div>
  );
};
