import axios from "axios";

const apiClient = axios.create({
  baseURL: "/blog",
  timeout: 5000,
});

export default apiClient;
