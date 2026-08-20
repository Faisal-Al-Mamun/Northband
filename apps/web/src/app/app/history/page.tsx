import { redirect } from "next/navigation";

export default function HistoryRedirect() {
  redirect("/app/attempts");
}
