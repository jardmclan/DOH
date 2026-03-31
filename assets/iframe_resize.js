
function sendHeightToParent(id) {
  const height = document.documentElement.scrollHeight;

  // post message with target origin as bh808 site
  window.parent.postMessage({
    messageType: "IFrameHeight",
    id,
    height: height
  }, "https://bh808.hawaii.gov/");
}


const urlParams = new URLSearchParams(window.location.search);
const frameId = urlParams.get("frameID");
// ignore if frameID not provided in URL params
if(frameId) {
  // Send height when the page loads
  window.addEventListener("load", () => {
    sendHeightToParent(frameId)
  });
  // Send height when resize observer indicates a change in size
  const resizeObserver = new ResizeObserver(() => {
    sendHeightToParent(frameId);
  });
  // Have resize observer monitor the document body
  resizeObserver.observe(document.body);
}
