import { Suspense } from "react";
import LiveSessionRoom from "@/components/session/LiveSessionRoom";

export default function LiveSessionPage() {
  return (
    <Suspense
      fallback={
        <main className="min-h-screen bg-[#071026] p-8 text-center text-qace-muted">
          Loading session…
        </main>
      }
    >
      <LiveSessionRoom />
    </Suspense>
  );
}
