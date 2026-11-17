"use client";
import { useState } from "react";
import { DEFAULT_CONTROLLER, DistrictView } from "@/components/district/district-view";
import { PageHeader } from "@/components/page-shell";
export default function District(){const [controller,setController]=useState(DEFAULT_CONTROLLER);return <><PageHeader title="District explorer" page="district"/><DistrictView controller={controller} onController={setController}/></>}