import axios from "axios";

const API_BASE = "http://localhost:8000"; // FastAPI base URL

export const getMeetings = async () => {
  return axios.get(`${API_BASE}/meetings`);
};

export const getMeetingDetails = async (meetingId) => {
  return axios.get(`${API_BASE}/meeting/${meetingId}`);
};

export const getFeedback = async () => {
  return axios.get(`${API_BASE}/feedback`);
};
