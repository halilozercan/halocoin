import React, { Component } from 'react';
import darkBaseTheme from 'material-ui/styles/baseThemes/darkBaseTheme';
import MuiThemeProvider from 'material-ui/styles/MuiThemeProvider';
import getMuiTheme from 'material-ui/styles/getMuiTheme';
import {
  green500, green700,
  pinkA200,
  grey100, grey300, grey400, grey500,
  white, darkBlack, fullBlack,
} from 'material-ui/styles/colors';
import MainPage from './MainPage.js';
import ChooseWallet from './ChooseWallet.js';
import io from 'socket.io-client';
import axios from 'axios';
import Snackbar from 'material-ui/Snackbar';

const muiTheme = getMuiTheme({
  palette: {
    primary1Color: green500,
    primary2Color: green700,
    primary3Color: grey400,
    accent1Color: pinkA200,
    accent2Color: grey100,
    accent3Color: grey500,
    textColor: darkBlack,
    alternateTextColor: white,
    canvasColor: white,
    borderColor: grey300,
    pickerHeaderColor: green500,
    shadowColor: fullBlack,
  },
  appBar: {
    height: 60,
  },
});


class App extends Component {
  constructor(props) {
    super(props);
    this.state = {
      "status": null
    }
    this.pageChanged = this.pageChanged.bind(this);
    this.checkDefault = this.checkDefault.bind(this);
    this.notify = this.notify.bind(this);
    this.socket = io('http://0.0.0.0:7001');

    this.socket.on('changed_default_wallet', (socket) => {
      this.checkDefault();
    });

    this.socket.on('new_tx_in_pool', (socket) => {

    });
  }

  componentDidMount() {
    axios.get('/').then((response) => {
      this.setState((state) => {
        state.status = 'running';
        return state;
      });
      this.checkDefault();
    }).catch((error) => {
      console.log(error);
      this.setState((state) => {
        state.status = 'closed';
        return state;
      });
    });
  }

  pageChanged(newPage) {
    this.setState({"page": newPage});
  }

  checkDefault() {
    axios.get("/info_wallet").then((response) => {
      let data = response.data;
      if(data.hasOwnProperty('address')) {
        this.setState((state) => {
          state.status = 'yes_dw';
          return state;
        });
      }
      else {
        this.setState((state) => {
          state.status = 'no_dw';
          return state;
        });
      }
    }).catch((error) => {
      console.log(error);
      this.setState((state) => {
        state.status = 'closed';
        return state;
      });
    });
  }

  sleep = (time) => {
    return new Promise((resolve) => setTimeout(resolve, time));
  }

  notify = (message, type, pos='bc') => {
    /*this._notificationSystem.addNotification({
      message: message,
      level: type,
      position: pos
    });*/
    this.setState({
      notificationOpen: true,
      notificationMessage: message
    })
  }

  handleRequestClose = () => {
    this.setState({
      notificationOpen: false
    })
  }

  render() {
    let page = <div />;
    if(this.state.status === null) {
      page = <div>Connecting to Coinami Engine</div>;
    }
    else if(this.state.status === "running") {
      page = <div>Checking your wallet</div>;
    }
    else if(this.state.status === "closed") {
      page = <div>Could not connect to Coinami Engine :(</div>;
    }
    else if(this.state.status === "yes_dw") {
      page = <MainPage socket={this.socket} notify={this.notify}/>;
    }
    else if(this.state.status === "no_dw") {
      page = <ChooseWallet socket={this.socket} notify={this.notify}/>;
    }

    return (
      <MuiThemeProvider muiTheme={muiTheme}>
        <div className="wrapper">
          <div className="content">
            {page}
          </div>
          <Snackbar
            open={this.state.notificationOpen}
            message={this.state.notificationMessage}
            autoHideDuration={4000}
            onRequestClose={this.handleRequestClose}
            bodyStyle={{ height: 'auto', lineHeight: '28px', padding: 12, whiteSpace: 'pre-line' }}
          />
        </div>
      </MuiThemeProvider>
    );
  }
}

export default App;
