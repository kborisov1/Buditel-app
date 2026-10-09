import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../../api/client";

export function useEntries(filters: { type?: string; q?: string } = {}) {
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

/** Progress changes what is unlocked, so every cached learner query is refetched. */
export function useRefreshProgress() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ predicate: (q) => q.queryKey[0] !== "me" });
}

export function useFinishedReading(slug: string) {
  const refresh = useRefreshProgress();
  return useMutation({
    mutationFn: () => api.finishedReading(slug),
    onSuccess: refresh,
  });
}
