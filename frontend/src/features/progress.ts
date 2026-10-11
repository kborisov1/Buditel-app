import { useQueryClient } from "@tanstack/react-query";

/** Anything that awards XP or changes due dates makes cached learner data stale. */
export function useRefreshLearnerData() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ predicate: (q) => q.queryKey[0] !== "me" });
}
