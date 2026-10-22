import { useState, useEffect } from 'react';
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  MarkerType,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { ShieldCheck, BookOpen, UserCheck, Calendar, Info, Layers, RefreshCw } from 'lucide-react';
import { fetchAssetSubgraph } from '../api';

interface GraphExplorerProps {
  initialAssetId?: string;
}

export const GraphExplorer: React.FC<GraphExplorerProps> = ({ initialAssetId = 'P-101' }) => {
  const [selectedAssetId, setSelectedAssetId] = useState<string>(initialAssetId);
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedItem, setSelectedItem] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(false);

  const loadGraph = async (assetId: string) => {
    setLoading(true);
    try {
      const data = await fetchAssetSubgraph(assetId);
      
      // Enhance nodes with colors based on type
      const styledNodes = data.nodes.map((n: any) => {
        let bg = '#1e293b';
        let border = '#334155';
        let color = '#f8fafc';

        if (n.type === 'assetNode') {
          bg = '#1d4ed8'; // Blue
          border = '#3b82f6';
        } else if (n.type === 'componentNode') {
          bg = '#0f766e'; // Teal
          border = '#14b8a6';
        } else if (n.type === 'incidentNode') {
          bg = '#047857'; // Emerald
          border = '#10b981';
        } else if (n.type === 'causeNode') {
          bg = '#b45309'; // Amber
          border = '#f59e0b';
        }

        return {
          ...n,
          style: {
            background: bg,
            color: color,
            border: `2px solid ${border}`,
            borderRadius: '12px',
            padding: '10px 14px',
            fontSize: '12px',
            fontWeight: 600,
            boxShadow: '0 4px 6px -1px rgba(0,0,0,0.2)',
          },
        };
      });

      const styledEdges = data.edges.map((e: any) => ({
        ...e,
        markerEnd: {
          type: MarkerType.ArrowClosed,
          width: 14,
          height: 14,
          color: e.style?.stroke || '#94a3b8',
        },
      }));

      setNodes(styledNodes);
      setEdges(styledEdges);
    } catch (e) {
      console.error('Failed to load subgraph', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadGraph(selectedAssetId);
  }, [selectedAssetId]);

  const onNodeClick = (_: any, node: any) => {
    setSelectedItem({ type: 'node', data: node.data, id: node.id });
  };

  const onEdgeClick = (_: any, edge: any) => {
    setSelectedItem({ type: 'edge', data: edge, id: edge.id });
  };

  return (
    <div className="space-y-4">
      {/* Asset Filter Toolbar */}
      <div className="flex items-center justify-between bg-white dark:bg-slate-900 p-4 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
        <div className="flex items-center gap-3">
          <Layers className="w-5 h-5 text-blue-600 dark:text-blue-400" />
          <span className="text-sm font-semibold text-slate-900 dark:text-white">
            Neighborhood Subgraph for:
          </span>
          <select
            value={selectedAssetId}
            onChange={(e) => setSelectedAssetId(e.target.value)}
            className="text-xs p-2 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white font-mono font-semibold"
          >
            <option value="P-101">P-101 (Boiler Feed Pump A)</option>
            <option value="P-102">P-102 (Transfer Pump B - Superseded Rev A)</option>
            <option value="P-103">P-103 (Condensate Pump C)</option>
            <option value="M-104">M-104 (Feed Motor A)</option>
            <option value="M-105">M-105 (Transfer Motor B)</option>
          </select>
        </div>

        <button
          onClick={() => loadGraph(selectedAssetId)}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 text-xs text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Main Graph Visualization Canvas */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 h-[600px]">
        <div className="lg:col-span-3 rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-950 overflow-hidden relative shadow-inner">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeClick={onNodeClick}
            onEdgeClick={onEdgeClick}
            fitView
          >
            <Controls className="!bg-slate-800 !border-slate-700 !text-white" />
            <MiniMap
              className="!bg-slate-900 !border-slate-800"
              nodeColor={() => '#3b82f6'}
            />
            <Background color="#334155" gap={20} size={1} />
          </ReactFlow>
        </div>

        {/* Provenance Details Side Panel */}
        <div className="bg-white dark:bg-slate-900 rounded-2xl p-5 border border-slate-200 dark:border-slate-800 shadow-sm overflow-y-auto space-y-4">
          <div className="flex items-center gap-2 border-b border-slate-100 dark:border-slate-800 pb-3">
            <Info className="w-4 h-4 text-blue-500" />
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-900 dark:text-white">
              Provenance Inspector
            </h4>
          </div>

          {selectedItem ? (
            <div className="space-y-3 text-xs">
              <div>
                <span className="text-[10px] uppercase font-mono text-slate-400">Selected Identifier</span>
                <div className="font-mono font-bold text-slate-900 dark:text-white text-sm">
                  {selectedItem.id}
                </div>
              </div>

              {selectedItem.data?.label && (
                <div>
                  <span className="text-[10px] uppercase font-mono text-slate-400">Label</span>
                  <div className="font-semibold text-slate-800 dark:text-slate-200">
                    {selectedItem.data.label}
                  </div>
                </div>
              )}

              {/* Provenance Details for Nodes */}
              {selectedItem.data?.raw && (
                <div className="p-3 bg-slate-50 dark:bg-slate-800/60 rounded-xl space-y-2 border border-slate-100 dark:border-slate-800">
                  <div className="flex items-center gap-2 text-emerald-600 dark:text-emerald-400 font-semibold text-[11px]">
                    <ShieldCheck className="w-3.5 h-3.5" />
                    <span>Verified Knowledge Node</span>
                  </div>

                  {selectedItem.data.raw.approved_by && (
                    <div className="flex items-center gap-1.5 text-slate-600 dark:text-slate-300">
                      <UserCheck className="w-3.5 h-3.5 text-blue-500" />
                      <span>Approved by: <strong>{selectedItem.data.raw.approved_by}</strong></span>
                    </div>
                  )}

                  {selectedItem.data.raw.incident_date && (
                    <div className="flex items-center gap-1.5 text-slate-600 dark:text-slate-300">
                      <Calendar className="w-3.5 h-3.5 text-purple-500" />
                      <span>Date: {selectedItem.data.raw.incident_date}</span>
                    </div>
                  )}

                  {selectedItem.data.raw.source_doc_id && (
                    <div className="flex items-center gap-1.5 text-slate-600 dark:text-slate-300 font-mono text-[11px]">
                      <BookOpen className="w-3.5 h-3.5 text-amber-500" />
                      <span>
                        {selectedItem.data.raw.source_doc_id} • §{selectedItem.data.raw.section}
                      </span>
                    </div>
                  )}

                  {selectedItem.data.raw.resolution_notes && (
                    <div className="mt-2 text-[11px] text-slate-600 dark:text-slate-400 italic">
                      "{selectedItem.data.raw.resolution_notes}"
                    </div>
                  )}
                </div>
              )}

              {/* Provenance for Edges */}
              {selectedItem.type === 'edge' && (
                <div className="p-3 bg-slate-50 dark:bg-slate-800/60 rounded-xl space-y-2 border border-slate-100 dark:border-slate-800">
                  <div className="text-[11px] text-slate-600 dark:text-slate-400">
                    Source: <code className="text-blue-500">{selectedItem.data.source}</code>
                  </div>
                  <div className="text-[11px] text-slate-600 dark:text-slate-400">
                    Target: <code className="text-indigo-500">{selectedItem.data.target}</code>
                  </div>
                  <div className="text-[11px] text-slate-600 dark:text-slate-400">
                    Relationship: <strong>{selectedItem.data.label}</strong>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-12 text-slate-400 text-xs">
              Click any node or edge in the graph to inspect its full provenance, approval metadata, and manual references.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
