import client from './client'
import type { ZoneDiagram, ZoneDiagramPin } from '../types'

export const zoneDiagramApi = {
  list: (areaId: string): Promise<ZoneDiagram[]> =>
    client.get(`/areas/${areaId}/zone-diagrams`).then((r) => r.data),

  create: (
    areaId: string,
    body: { name: string; image_url: string; image_width?: number; image_height?: number }
  ): Promise<ZoneDiagram> =>
    client.post(`/areas/${areaId}/zone-diagrams`, body).then((r) => r.data),

  get: (diagramId: string): Promise<ZoneDiagram> =>
    client.get(`/zone-diagrams/${diagramId}`).then((r) => r.data),

  addPin: (
    diagramId: string,
    body: { object_id: string; x_pct: number; y_pct: number }
  ): Promise<ZoneDiagramPin> =>
    client.post(`/zone-diagrams/${diagramId}/pins`, body).then((r) => r.data),

  updatePin: (
    diagramId: string,
    pinId: string,
    body: { x_pct: number; y_pct: number }
  ): Promise<ZoneDiagramPin> =>
    client.put(`/zone-diagrams/${diagramId}/pins/${pinId}`, body).then((r) => r.data),

  deletePin: (diagramId: string, pinId: string): Promise<void> =>
    client.delete(`/zone-diagrams/${diagramId}/pins/${pinId}`).then(() => undefined),
}
