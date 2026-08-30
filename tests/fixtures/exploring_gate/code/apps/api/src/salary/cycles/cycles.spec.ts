// Deliberate violation fixture: an assertion/spec test file living under an
// `exploring` Story's touches: path. `validate` must flag this as an ERROR
// (smoke test only until the Story goes `settled`). Not executed by anything.
describe("salary cycles", () => {
  it("splits a 10-day cycle", () => {
    expect(true).toBe(true);
  });
});
