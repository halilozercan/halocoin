const electron = require('electron');
const axios = require('axios');
// Module to control application life.
const app = electron.app;
// Module to create native browser window.
const BrowserWindow = electron.BrowserWindow;

const path = require('path');
const url = require('url');

// Keep a global reference of the window object, if you don't, the window will
// be closed automatically when the JavaScript object is garbage collected.
let mainWindow;

function createWindow() {
    // Create the browser window.
    mainWindow = new BrowserWindow({
      title: 'Halocoin', 
      width: 900, 
      height: 660, 
      webPreferences: {webSecurity: false},
      icon: path.join(__dirname, '/../public/coins.png')
    });

    const startUrl = process.env.ELECTRON_START_URL || url.format({
            pathname: path.join(__dirname, '/../build/index.html'),
            protocol: 'file:',
            slashes: true
        });
    console.log('start: ' + startUrl);
    mainWindow.loadURL(startUrl);

    // Emitted when the window is closed.
    mainWindow.on('closed', function () {
        // Dereference the window object, usually you would store windows
        // in an array if your app supports multi windows, this is the time
        // when you should delete the corresponding element.
        mainWindow = null
    })
}

// Quit when all windows are closed.
app.on('window-all-closed', function () {
    // On OS X it is common for applications and their menu bar
    // to stay active until the user quits explicitly with Cmd + Q
    if (process.platform !== 'darwin') {
        app.quit()
    }
});

app.on('activate', function () {
    // On OS X it's common to re-create a window in the app when the
    // dock icon is clicked and there are no other windows open.
    if (mainWindow === null) {
        createWindow()
    }
});

let pyProc = null;

const createPyProc = () => {
  let python_exec = path.join(__dirname, '../halocoin');
  console.log('Executable location: ' + python_exec);
  pyProc = require('child_process').spawn(python_exec, ['start']);
  if (pyProc != null) {
    console.log('child process success');
    setTimeout(createWindow, 1000);
  }
}

const exitPyProc = () => {
  pyProc.kill('SIGINT')
  pyProc = null
  pyPort = null
}

//app.on('ready', createPyProc);
app.on('ready', createWindow);
app.on('will-quit', exitPyProc);

// In this file you can include the rest of your app's specific main process
// code. You can also put them in separate files and require them here.
