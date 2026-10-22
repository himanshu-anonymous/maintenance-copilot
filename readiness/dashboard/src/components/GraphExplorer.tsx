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
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from './ui/card';
import { Button } from './ui/button';

interface GraphExplorerProps {
  initialAssetId?: string;
}

export const GraphExplorer = ({ initialAssetId = 'P-101' }: GraphExplorerProps) => {
  const [selectedAssetId, setSelectedAssetId] = useState<string>(initialAssetId);
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedItem, setSelectedItem] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(false);

  const loadGraph = async (assetId: string) => {
    setLoading(true);
    try {
      const data = await fetchAssetSubgraph(assetId);

      const styledNodes = data.nodes.map((n: any) => {
        let bg = '#18181b';
        let border = '#3f3f46';
        let color = '#fafafa';

        if (n.type === 'assetNode') {
          bg = '#09090b';
          border = '#71717a';
        } else if (n.type === 'componentNode') {
          bg = '#14532d';
          border = '#22c55e';
        } else if (n.type === 'incidentNode') {
          bg = '#065f46';
          border = '#10b981';
        } else if (n.type === 'causeNode') {
          bg = '#78350f';
          border = '#f59e0b';
        }

        return {
          ...n,
          style: {
            background: bg,
            color: color,
            border: `1px solid ${border}`,
            borderRadius: '8px',
            padding: '8px 12px',
            fontSize: '11px',
            fontFamily: 'Geist, Inter, sans-serif',
            fontWeight: 500,
            boxShadow: '0 1px 2px 0 rgba(0,0,0,0.05)',
          },
        };
      });

      const styledEdges = data.edges.map((e: any) => ({
        ...e,
        markerEnd: {
          type: MarkerType.ArrowClosed,
          width: 12,
          height: 12,
          color: e.style?.stroke || '#71717a',
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
      <Card>
        <CardContent className="p-3 flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-2.5">
            <Layers className="h-4 w-4 text-zinc-500" />
            <span className="text-xs font-semibold text-zinc-900 dark:text-zinc-100">
              Neighborhood Subgraph for:
            </span>
            <select
              value={selectedAssetId}
              onChange={(e) => setSelectedAssetId(e.target.value)}
              className="text-xs p-1.5 rounded-md border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-50 font-mono font-medium"
            >
              <option value="P-101">P-101 (Primary Feed Pump A)</option>
              <option value="P-102">P-102 (Transfer Pump B - Superseded Rev A)</option>
              <option value="P-103">P-103 (Condensate Pump C)</option>
              <option value="M-104">M-104 (Feed Motor A)</option>
              <option value="M-105">M-105 (Transfer Motor B)</option>
            </select>
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={() => loadGraph(selectedAssetId)}
            className="h-8 gap-1.5 text-xs"
          >
            <RefreshCw className={`h-3 w-3 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </Button>
        </CardContent>
      </Card>

      {/* Main Canvas & Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 h-[600px]">
        <div className="lg:col-span-3 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-950 overflow-hidden relative shadow-xs">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeClick={onNodeClick}
            onEdgeClick={onEdgeClick}
            fitView
          >
            <Controls className="!bg-zinc-900 !border-zinc-800 !text-zinc-100" />
            <MiniMap className="!bg-zinc-950 !border-zinc-800" nodeColor={() => '#52525b'} />
            <Background color="#27272a" gap={16} size={1} />
          </ReactFlow>
        </div>

        {/* Provenance Side Panel */}
        <Card className="h-full flex flex-col justify-between overflow-y-auto">
          <div>
            <CardHeader className="p-4 pb-3 border-b border-zinc-100 dark:border-zinc-800">
              <div className="flex items-center gap-2">
                <Info className="h-4 w-4 text-zinc-500" />
                <CardTitle className="text-xs uppercase tracking-wider font-mono">
                  Provenance Inspector
                </CardTitle>
              </div>
              <CardDescription className="text-[11px]">
                Click any graph node or relationship edge to inspect verified origin metadata
              </CardDescription>
            </CardHeader>

            <CardContent className="p-4 space-y-3 text-xs">
              {selectedItem ? (
                <div className="space-y-3">
                  <div>
                    <span className="text-[10px] uppercase font-mono text-zinc-400">Node Identifier</span>
                    <div className="font-mono font-bold text-zinc-900 dark:text-zinc-50">
                      {selectedItem.id}
                    </div>
                  </div>

                  {selectedItem.data?.label && (
                    <div>
                      <span className="text-[10px] uppercase font-mono text-zinc-400">Label</span>
                      <div className="font-medium text-zinc-800 dark:text-zinc-200">
                        {selectedItem.data.label}
                      </div>
                    </div>
                  )}

                  {selectedItem.data?.raw && (
                    <div className="p-3 bg-zinc-50 dark:bg-zinc-900 rounded-lg space-y-2 border border-zinc-200 dark:border-zinc-800">
                      <div className="flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400 font-semibold text-[11px]">
                        <ShieldCheck className="h-3.5 w-3.5" />
                        <span>Verified Precedent Node</span>
                      </div>

                      {selectedItem.data.raw.approved_by && (
                        <div className="flex items-center gap-1.5 text-zinc-600 dark:text-zinc-300">
                          <UserCheck className="h-3.5 w-3.5 text-zinc-500" />
                          <span>Approved by: <strong>{selectedItem.data.raw.approved_by}</strong></span>
                        </div>
                      )}

                      {selectedItem.data.raw.incident_date && (
                        <div className="flex items-center gap-1.5 text-zinc-600 dark:text-zinc-300">
                          <Calendar className="h-3.5 w-3.5 text-zinc-500" />
                          <span>Date: {selectedItem.data.raw.incident_date}</span>
                        </div>
                      )}

                      {selectedItem.data.raw.source_doc_id && (
                        <div className="flex items-center gap-1.5 text-zinc-600 dark:text-zinc-300 font-mono text-[11px]">
                          <BookOpen className="h-3.5 w-3.5 text-zinc-500" />
                          <span>
                            {selectedItem.data.raw.source_doc_id} • §{selectedItem.data.raw.section}
                          </span>
                        </div>
                      )}

                      {selectedItem.data.raw.resolution_notes && (
                        <p className="mt-2 text-[11px] text-zinc-500 italic">
                          "{selectedItem.data.raw.resolution_notes}"
                        </p>
                      )}
                    </div>
                  )}

                  {selectedItem.type === 'edge' && (
                    <div className="p-3 bg-zinc-50 dark:bg-zinc-900 rounded-lg space-y-1.5 border border-zinc-200 dark:border-zinc-800 text-[11px]">
                      <div>Source: <code className="text-zinc-900 dark:text-zinc-100 font-semibold">{selectedItem.data.source}</code></div>
                      <div>Target: <code className="text-zinc-900 dark:text-zinc-100 font-semibold">{selectedItem.data.target}</code></div>
                      <div>Edge Type: <strong>{selectedItem.data.label}</strong></div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center py-10 text-zinc-400 text-xs">
                  Select a node or edge to view its verified provenance chain.
                </div>
              )}
            </CardContent>
          </div>
        </Card>
      </div>
    </div>
  );
};
