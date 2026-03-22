import client from './client'
import type { ScheduleResponse } from '../types'

export const scheduleApi = {
  runCpm: (instanceId: string): Promise<ScheduleResponse> =>
    client.post(`/workflow-instances/${instanceId}/schedule/run`).then((r) => r.data),

  getSchedule: (instanceId: string): Promise<ScheduleResponse> =>
    client.get(`/workflow-instances/${instanceId}/schedule`).then((r) => r.data),

  updateTaskDuration: (
    instanceId: string,
    taskId: string,
    payload: { duration_days?: number; effort_hours?: number; assigned_resource_id?: string | null },
  ): Promise<ScheduleResponse> =>
    client
      .put(`/workflow-instances/${instanceId}/tasks/${taskId}/duration`, payload)
      .then((r) => r.data),
}

export const exportApi = {
  objectsCsvUrl: (projectId: string) => `/projects/${projectId}/export/objects.csv`,
  tasksCsvUrl: (projectId: string) => `/projects/${projectId}/export/tasks.csv`,
  readinessCsvUrl: (projectId: string) => `/projects/${projectId}/export/readiness.csv`,
}
