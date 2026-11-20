"use client";
import { useState } from "react";
import { DEFAULT_CONTROLLER, DistrictView } from "@/components/district/district-view";
import { PageHeader, PhaseNote } from "@/components/page-shell";
export default function District(){const [controller,setController]=useState(DEFAULT_CONTROLLER);return <><PageHeader title="District explorer" page="district"/><PhaseNote links={[{href:"/overview/",label:"All phases on one map"},{href:"/scenarios/",label:"With solar and battery"},{href:"/explorer/",label:"With cooling"}]}><b className="font-semibold">Phase A simulation:</b> heat pumps, tanks and grid electricity; solar, battery and cooling come in later phases.</PhaseNote><DistrictView controller={controller} onController={setController}/></>}