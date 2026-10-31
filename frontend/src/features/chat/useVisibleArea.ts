import { useEffect } from "react"

// Is the phone keyboard up? It only shows while a text box has the focus.
function typingInABox() {
  const box = document.activeElement
  return box instanceof HTMLInputElement || box instanceof HTMLTextAreaElement
}

// On an iPhone the keyboard doesn't make the page shorter: it covers the bottom
// of it, and Safari slides the whole page up to show the box you tapped.
// visualViewport is the part of the page you can actually see. This keeps its
// height and top in two CSS variables, so the chat screen fits exactly in it:
// header at the top, message box just above the keyboard (D8).
// It also locks the page (the page-locked class in index.css), so a finger on
// the header, the message box or an empty chat can't drag the whole screen.
export function useVisibleArea() {
  useEffect(() => {
    const root = document.documentElement
    root.classList.add("page-locked")
    const visible = window.visualViewport
    if (!visible) return () => root.classList.remove("page-locked") // a very old browser: the screen uses 100dvh

    const fit = () => {
      // Pinch-zoomed in: you see less because you zoomed, not because of a keyboard. Leave the screen as it is.
      if (visible.scale > 1.01) return
      root.style.setProperty("--visible-height", `${visible.height}px`)
      // Follow Safari's slide only while the keyboard is up. Any other move is
      // the page bouncing under a finger, and following it would move the
      // screen the wrong way, or leave the header cut off.
      const top = typingInABox() ? Math.max(0, visible.offsetTop) : 0
      root.style.setProperty("--visible-top", `${top}px`)
    }

    fit()
    // resize: the keyboard opened or closed. scroll: Safari slid the page.
    visible.addEventListener("resize", fit)
    visible.addEventListener("scroll", fit)
    return () => {
      visible.removeEventListener("resize", fit)
      visible.removeEventListener("scroll", fit)
      root.style.removeProperty("--visible-height")
      root.style.removeProperty("--visible-top")
      root.classList.remove("page-locked")
    }
  }, [])
}
