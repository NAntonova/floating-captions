import Cocoa
import WebKit
import sys
import objc
from PyObjCTools import AppHelper

class DraggableWebView(WebKit.WKWebView):
    def acceptsFirstMouse_(self, event):
        return True

    def mouseDown_(self, event):
        # Get mouse location in webview coordinates
        point = self.convertPoint_fromView_(event.locationInWindow(), None)
        bounds = self.bounds()
        
        # Close button area is at the top right corner.
        # We assume a 45x45 pixels zone in the top right.
        is_near_close_button = (point.x > bounds.size.width - 45) and (point.y > bounds.size.height - 45)
        
        if is_near_close_button:
            # Pass the event normally to let the HTML button handle it
            objc.super(DraggableWebView, self).mouseDown_(event)
        else:
            # Initiate native window drag immediately on first mouse down (single-click dragging)
            self.window().performWindowDragWithEvent_(event)

class CloseMessageHandler(Cocoa.NSObject):
    def userContentController_didReceiveScriptMessage_(self, controller, message):
        if message.name() == "closeHandler":
            Cocoa.NSApp.terminate_(None)

class UIDelegate(Cocoa.NSObject):
    def webViewDidClose_(self, webView):
        # Close the window and exit the script
        Cocoa.NSApp.terminate_(None)

class CustomWindow(Cocoa.NSWindow):
    def canBecomeKeyWindow(self):
        return True
    def canBecomeMainWindow(self):
        return True

class AppDelegate(Cocoa.NSObject):
    def applicationDidFinishLaunching_(self, notification):
        # Window size & position (bottom right corner by default)
        screen = Cocoa.NSScreen.mainScreen()
        screen_rect = screen.visibleFrame()
        width, height = 450, 300
        x = screen_rect.origin.x + screen_rect.size.width - width - 20
        y = screen_rect.origin.y + 20 # bottom right (Mac coordinates starts from bottom-left)
        rect = Cocoa.NSMakeRect(x, y, width, height)
        
        # Borderless window with resizable mask
        style = 0 | (1 << 3)
        
        self.window = CustomWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            rect,
            style,
            Cocoa.NSBackingStoreBuffered,
            False
        )
        
        # Configure transparency & level
        self.window.setOpaque_(False)
        self.window.setBackgroundColor_(Cocoa.NSColor.clearColor())
        self.window.setHasShadow_(True)
        self.window.setLevel_(Cocoa.NSFloatingWindowLevel) # always-on-top
        self.window.setMovableByWindowBackground_(True) # draggable by background click
        
        # Make the window visible across all virtual desktops/Spaces
        # NSWindowCollectionBehaviorCanJoinAllSpaces = 1 << 0
        # NSWindowCollectionBehaviorFullScreenAuxiliary = 1 << 4
        self.window.setCollectionBehavior_(1 | 16)
        
        # Accept mouse events even if borderless
        self.window.setAcceptsMouseMovedEvents_(True)
        
        # Create WebView Configuration
        userController = WebKit.WKUserContentController.alloc().init()
        self.closeHandler = CloseMessageHandler.alloc().init()
        userController.addScriptMessageHandler_name_(self.closeHandler, "closeHandler")
        
        config = WebKit.WKWebViewConfiguration.alloc().init()
        config.setUserContentController_(userController)
        
        # Create WebView filling the entire window
        self.webView = DraggableWebView.alloc().initWithFrame_configuration_(
            self.window.contentView().bounds(),
            config
        )
        self.webView.setValue_forKey_(False, "drawsBackground")
        self.webView.setOpaque_(False)
        self.webView.setBackgroundColor_(Cocoa.NSColor.clearColor())
        
        # Autoresize webview with window
        self.webView.setAutoresizingMask_(Cocoa.NSViewWidthSizable | Cocoa.NSViewHeightSizable)
        self.window.contentView().addSubview_(self.webView)
        
        # Bind UIDelegate to handle window.close()
        self.uiDelegate = UIDelegate.alloc().init()
        self.webView.setUIDelegate_(self.uiDelegate)
        
        # Load URL
        url = Cocoa.NSURL.URLWithString_("http://localhost:8000/static/pip.html")
        request = Cocoa.NSURLRequest.requestWithURL_(url)
        self.webView.loadRequest_(request)
        
        # Show window
        Cocoa.NSApp.activateIgnoringOtherApps_(True)
        self.window.makeKeyAndOrderFront_(None)
        self.window.orderFrontRegardless()

_delegate = None

def main():
    global _delegate
    app = Cocoa.NSApplication.sharedApplication()
    app.setActivationPolicy_(1) # NSApplicationActivationPolicyAccessory = 1
    _delegate = AppDelegate.alloc().init()
    app.setDelegate_(_delegate)
    AppHelper.runEventLoop()

if __name__ == "__main__":
    main()
