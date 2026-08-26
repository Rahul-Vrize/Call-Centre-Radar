// The core per-call view — GET /calls/{id}. Playable recording, transcript,
// mood timeline, and every judgment carrying a clickable evidence chip.
import { getCall } from "@/lib/api";
import ApiNotice from "@/components/ApiNotice";
import CallView from "@/components/CallView";

export default async function CallDetailPage({
  params,
}: {
  params: Promise<{ callId: string }>;
}) {
  const { callId } = await params;
  const { data: call, error } = await getCall(callId);

  if (error || !call) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-semibold">Call {callId}</h1>
        <ApiNotice error={error ?? "No call returned."} />
      </div>
    );
  }

  return <CallView call={call} />;
}
