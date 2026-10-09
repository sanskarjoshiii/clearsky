import { Building2, Factory, SlidersHorizontal, Truck } from "lucide-react";
import { RailLayout, type NavItem } from "../../components/Shell";

const ITEMS: NavItem[] = [
  { to: "/buyer", label: "Overview", icon: Factory, end: true },
  { to: "/buyer/deliveries", label: "Deliveries", icon: Truck },
  { to: "/buyer/demand", label: "Demand and price", short: "Demand", icon: SlidersHorizontal },
  { to: "/buyer/profile", label: "Profile", icon: Building2 },
];

/** Buyer (industry) app: the same quiet frame as the admin app with a lighter rail and no simulator. */
export function BuyerLayout() {
  return <RailLayout label="Buyer" items={ITEMS} />;
}

export const BUYER_TYPE: Record<string, string> = {
  pellet: "Pellet plant",
  cbg: "CBG plant",
  boiler: "Industrial boiler",
  biomass_power: "Biomass power",
};
