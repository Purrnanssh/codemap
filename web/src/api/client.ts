const API_BASE = "http://127.0.0.1:8000/api/v1";

export interface JobStatus {
  job_id: string;
  status: "queued" | "processing" | "completed" | "failed";
  error_msg: string | null;
}

export const codemapApi = {
  async ingestWorkspace(path: string): Promise<string> {
    const response = await fetch(`${API_BASE}/workspaces/ingest`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path }),
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Failed to start ingestion");
    }
    
    const data = await response.json();
    return data.job_id;
  },

  async pollJobStatus(jobId: string): Promise<JobStatus> {
    const response = await fetch(`${API_BASE}/jobs/${jobId}`);
    if (!response.ok) throw new Error("Failed to fetch job status");
    return response.json();
  },

  async getGraph(jobId: string): Promise<any> {
    const response = await fetch(`${API_BASE}/workspaces/${jobId}/graph`);
    if (!response.ok) throw new Error("Failed to fetch graph");
    return response.json();
  }
};
