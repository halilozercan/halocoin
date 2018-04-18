import React, { Component } from 'react';
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
import Snackbar from 'material-ui/Snackbar';
import {Card,CardText} from 'material-ui/Card';

import {connect} from 'react-redux';
import {bindActionCreators} from 'redux';
import * as loginActions from './actions/loginActions';
import PropTypes from 'prop-types';

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

    console.log("Login: " + this.props.jwtToken)
    console.log("Engine: " + this.props.engine)
    
    this.socket = io('http://0.0.0.0:7001');

    /*this.socket.on('connect', (socket => {
      //this.checkDefault();
    }));

    this.socket.on('disconnect', (socket => {
      //this.checkDefault();
    }));

    this.socket.on('changed_default_wallet', (socket) => {
      //this.checkDefault();
    });

    this.socket.on('new_tx_in_pool', (socket) => {

    });

    this.socket.on('new_block', (socket) => {
      //this.checkDefault();
    });

    this.socket.on('new_tx_in_pool', (socket) => {
      //this.checkDefault();
    });*/
  }

  componentDidMount() {
    this.props.loginActions.checkEngine();
  }

  pageChanged = (newPage) => {
    this.setState({"page": newPage});
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

  handleLogin = (walletName, password) => {
    this.props.loginActions.login(walletName, password);
  }

  handleLogout = () => {
    this.props.loginActions.logout();
  }

  render() {
    console.log("rendering " + this.props.jwtToken)
    let page = <div />;
    if(this.props.engine === "loading") {
      page = <Card style={{margin:"32px"}}>
              <CardText>
                Connecting to Halocoin Engine
              </CardText>
            </Card>;
    }
    else if(this.props.engine === "disconnected") {
      page = <Card style={{margin:"32px"}}>
              <CardText>
                Could not connect to Halocoin engine :(
              </CardText>
            </Card>;
    }
    else if(this.props.jwtToken !== null) {
      page = <MainPage  socket={this.socket} 
                        notify={this.notify}/>;
    }
    else if(this.props.jwtToken === null) {
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

App.propTypes = {
  loginActions: PropTypes.object,
  jwtToken: PropTypes.string,
  engine: PropTypes.string
};

function mapStateToProps(state) {
  return {
      jwtToken: state.jwtToken,
      engine: state.engine
  };
}

function mapDispatchToProps(dispatch) {
  return {
     loginActions: bindActionCreators(loginActions, dispatch)
  };
}

export default connect(
  mapStateToProps,
  mapDispatchToProps
)(App);
