import { useMutation, useQuery } from "@tanstack/react-query";
import { api, type EntryFilters } from "../../api/client";
import { useRefreshLearnerData } from "../progress";

export function useEntries(filters: EntryFilters = {}) {
  return useQuery({
    queryKey: ["entries", filters],
    queryFn: () => api.entries(filters),
  });
}

export function useEntry(slug: string | undefined) {
  return useQuery({
    queryKey: ["entry", slug],
    queryFn: () => api.entry(slug!),
    enabled: !!slug,
  });
}

export function useFinishedReading(slug: string) {
  const refresh = useRefreshLearnerData();
  return useMutation({
    mutationFn: () => api.finishedReading(slug),
    onSuccess: refresh,
  });
}
