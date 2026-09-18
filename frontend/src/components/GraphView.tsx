import React, { useEffect, useRef } from 'react';
import { Network } from 'vis-network';
import { DataSet } from 'vis-data';

interface GraphViewProps {
  nodesData: any[];
  edgesData: any[];
  onSelectNode: (nodeId: string) => void;
}

export const GraphView: React.FC<GraphViewProps> = ({ nodesData, edgesData, onSelectNode }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const networkRef = useRef<Network | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const nodes = new DataSet(nodesData);
    const edges = new DataSet(edgesData);

    const data = { nodes, edges };

    const options: any = {
      nodes: {
        borderWidth: 2,
        shadow: true,
        font: {
          color: '#ffffff',
          face: 'Inter, sans-serif',
          size: 12
        }
      },
      edges: {
        width: 1.5,
        smooth: {
          enabled: true,
          type: 'continuous',
          roundness: 0.2
        }
      },
      physics: {
        enabled: true,
        solver: 'forceAtlas2Based',
        forceAtlas2Based: {
          gravitationalConstant: -50,
          centralGravity: 0.01,
          springLength: 100,
          springConstant: 0.08,
          damping: 0.4
        },
        stabilization: {
          enabled: true,
          iterations: 150, // Auto-stabilization after 150 iterations to ensure 60 FPS
          updateInterval: 25
        }
      },
      interaction: {
        hover: true,
        tooltipDelay: 100,
        zoomView: true,
        dragView: true
      }
    };

    const network = new Network(containerRef.current, data, options);
    networkRef.current = network;

    // Freeze physics after stabilization for smooth rendering
    network.on('stabilizationIterationsDone', () => {
      network.setOptions({ physics: { enabled: false } });
    });

    network.on('click', (params) => {
      if (params.nodes && params.nodes.length > 0) {
        onSelectNode(params.nodes[0]);
      }
    });

    return () => {
      network.destroy();
    };
  }, [nodesData, edgesData]);

  return (
    <div
      ref={containerRef}
      style={{
        width: '100%',
        height: '100%',
        minHeight: '600px',
        background: 'radial-gradient(circle at 50% 50%, rgba(139, 92, 246, 0.03) 0%, transparent 80%)'
      }}
    />
  );
};
