import { getReleases, getLatestRelease, getReleaseByVersion, getPrimaryAssetForOS } from "../src/data/releases";

describe("Release Architecture & Data System", () => {
  test("getReleases returns non-empty array of releases", () => {
    const releases = getReleases();
    expect(releases.length).toBeGreaterThan(0);
  });

  test("getLatestRelease correctly resolves current latest version", () => {
    const latest = getLatestRelease();
    expect(latest).toBeDefined();
    expect(latest.version).toBe("v1.1.0");
    expect(latest.isLatest).toBe(true);
  });

  test("getReleaseByVersion finds existing release and returns undefined for unknown version", () => {
    const v11 = getReleaseByVersion("v1.1.0");
    expect(v11).toBeDefined();
    expect(v11?.version).toBe("v1.1.0");

    const v1 = getReleaseByVersion("v1.0.0");
    expect(v1).toBeDefined();
    expect(v1?.version).toBe("v1.0.0");

    const vUnknown = getReleaseByVersion("v9.9.9");
    expect(vUnknown).toBeUndefined();
  });

  test("getPrimaryAssetForOS returns appropriate asset or null for platform", () => {
    const latest = getLatestRelease();

    const linuxAsset = getPrimaryAssetForOS(latest, "linux");
    expect(linuxAsset).not.toBeNull();
    expect(linuxAsset?.type).toBe("deb");
    expect(linuxAsset?.available).toBe(true);

    const winAsset = getPrimaryAssetForOS(latest, "windows");
    expect(winAsset).not.toBeNull();
    expect(winAsset?.type).toBe("exe");
    expect(winAsset?.available).toBe(true);

    const macAsset = getPrimaryAssetForOS(latest, "macos");
    expect(macAsset).not.toBeNull();
    expect(macAsset?.type).toBe("dmg");
    expect(macAsset?.available).toBe(true); // macOS .dmg automated build is now fully active
  });
});
