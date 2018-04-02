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
import {Card, CardActions, CardHeader, CardText} from 'material-ui/Card';

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
      "status": null,
      "wallet_name": null,
      "account": null
    }
    
    this.socket = io('http://0.0.0.0:7001');

    this.socket.on('connect', (socket => {
      this.checkDefault();
    }));

    this.socket.on('disconnect', (socket => {
      this.checkDefault();
    }));

    this.socket.on('changed_default_wallet', (socket) => {
      this.checkDefault();
    });

    this.socket.on('new_tx_in_pool', (socket) => {

    });

    this.socket.on('new_block', (socket) => {
      this.checkDefault();
    });

    this.socket.on('new_tx_in_pool', (socket) => {
      this.checkDefault();
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

  pageChanged = (newPage) => {
    this.setState({"page": newPage});
  }

  checkDefault = () => {
    axios.get("/login/info").then((response) => {
      let data = response.data;
      if(data.success) {
        this.setState((state) => {
          state.status = 'logged_in';
          state.account = data.account;
          return state;
        });
      }
      else {
        this.setState((state) => {
          state.status = 'no_login';
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
      page = <Card style={{margin:"32px"}}>
              <CardText>
                Connecting to Halocoin Engine
              </CardText>
            </Card>;
    }
    else if(this.state.status === "running") {
      page = <Card style={{margin:"32px"}}>
              <CardText>
                Checking your wallet
              </CardText>
            </Card>;
    }
    else if(this.state.status === "closed") {
      page = <Card style={{margin:"32px"}}>
              <CardText>
                Could not connect to Halocoin engine :(
              </CardText>
            </Card>;
    }
    else if(this.state.status === "logged_in") {
      page = <MainPage  socket={this.socket} 
                        notify={this.notify} 
                        wallet_name={this.state.wallet_name} 
                        account={this.state.account}/>;
    }
    else if(this.state.status === "no_login") {
      page = <ChooseWallet  socket={this.socket} 
                            notify={this.notify}/>;
    }

    return (
      <MuiThemeProvider muiTheme={muiTheme}>
        <div className="wrapper">
          <div className="content" style={{overflowY:"hidden", overflowX:"hidden"}}>
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
