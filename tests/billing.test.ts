import { describe, expect, it } from "vitest";
import { checkoutForm } from "../src/billing.js";

describe("checkout", () => {
  it("uses an existing price, a 7-day card-free trial, and cancels if no card is added", () => {
    const params = checkoutForm({
      userId: "00000000-0000-4000-8000-000000000001",
      email: "dev@pagedrill.local",
      priceId: "price_from_env",
      baseUrl: "http://localhost:3000"
    });
    const keys = [...params.keys()];
    expect(params.get("line_items[0][price]")).toBe("price_from_env");
    expect(params.get("subscription_data[trial_period_days]")).toBe("7");
    expect(params.get("payment_method_collection")).toBe("if_required");
    expect(params.get("subscription_data[trial_settings][end_behavior][missing_payment_method]")).toBe("cancel");
    expect(keys.some((key) => key.includes("price_data") || key.includes("unit_amount"))).toBe(false);
  });
});
