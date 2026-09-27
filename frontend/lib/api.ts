import axios from "axios";

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001/api";

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Interceptor to automatically attach token
api.interceptors.request.use((config) => {
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, (error) => {
  return Promise.reject(error);
});

// Interceptor to handle authentication errors globally
api.interceptors.response.use((response) => {
  return response;
}, (error) => {
  if (error.response && error.response.status === 401) {
    if (typeof window !== "undefined") {
      localStorage.removeItem("token");
    }
  }
  return Promise.reject(error);
});

export const authApi = {
  register: async (data: any) => {
    const res = await api.post("/auth/register", data);
    return res.data;
  },
  login: async (username: string, password: string) => {
    const params = new URLSearchParams();
    params.append("username", username);
    params.append("password", password);
    const res = await api.post("/auth/token", params, {
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
    });
    if (res.data.access_token) {
      localStorage.setItem("token", res.data.access_token);
    }
    return res.data;
  },
  logout: () => {
    localStorage.removeItem("token");
  },
  me: async () => {
    const res = await api.get("/auth/me");
    return res.data;
  }
};

export const analysisApi = {
  upload: async (formData: FormData) => {
    if (formData.has("file") && !formData.has("image")) {
      formData.append("image", formData.get("file") as Blob);
    }
    const res = await api.post("/analysis/upload", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });
    return res.data;
  },
  getResults: async (id: string) => {
    const res = await api.get(`/analysis/${id}`);
    return res.data;
  },
  getPatientsHistory: async (search?: string) => {
    const res = await api.get("/patients/history", {
      params: search ? { search } : {},
    });
    return res.data;
  }
};

export const doctorApi = {
  search: async (lat: number, lon: number, radius: number = 30) => {
    const res = await api.get("/doctors/search", {
      params: { latitude: lat, longitude: lon, radius_km: radius },
    });
    return res.data;
  },
  bookAppointment: async (data: any) => {
    const res = await api.post("/appointments/book", data);
    return res.data;
  },
  getAppointments: async () => {
    const res = await api.get("/appointments");
    return res.data;
  }
};
