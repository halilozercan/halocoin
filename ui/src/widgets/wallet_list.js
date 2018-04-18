import React, { Component } from 'react';
import {List, ListItem} from 'material-ui/List';
import {Card, CardHeader, CardText} from 'material-ui/Card';
import RaisedButton from 'material-ui/RaisedButton';
import Dialog from 'material-ui/Dialog';
import TextField from 'material-ui/TextField';

import {connect} from 'react-redux';
import {bindActionCreators} from 'redux';
import * as loginActions from '../actions/loginActions';
import PropTypes from 'prop-types';

class WalletList extends Component {

  constructor(props) {
    super(props);
    this.state = {
      open: false
    }
  }

  downloadWallet(wallet_name) {
    setTimeout(() => {
      // server sent the url to the file!
      // now, let's download:
      window.open('/download_wallet?wallet_name=' + wallet_name);
      // you could also do:
      // window.location.href = response.file;
    }, 100);
  }

  handleOpen = (wallet_name) => {
    this.setState({open: true, name: wallet_name});
  };

  handleClose = () => {
    this.setState({open: false});
  };

  onPasswordChange = (e) => {
    this.setState({password: e.target.value});
  }

  login = () => {
    this.props.loginActions.login(this.state.name, this.state.password)
  }

  render() {
    let content = <div>There are no wallets</div>;
    if(this.props.wallets !== null && Object.keys(this.props.wallets).length > 0) {
      content = this.props.wallets.map((_row, i) => {
                    return <ListItem primaryText={_row} onClick={() => {this.handleOpen(_row);}} />;
                });
    }

    const actions = [
      <RaisedButton
        label="Ok"
        primary={true}
        keyboardFocused={true}
        onClick={this.login}
      />,
    ];

    return (
      <Card style={{"margin":16}}>
        <CardHeader
          title="Choose a Wallet"
          subtitle="Select one of the wallets created earlier"
        />
        <CardText>
          <List>
            {content}
          </List>
        </CardText>
        <Dialog
          title="Enter Password"
          actions={actions}
          modal={false}
          open={this.state.open}
          onRequestClose={this.handleClose}
        >
          <TextField
              fullWidth={true}
              floatingLabelText="Password"
              name="password"
              type="password"
              onChange={this.onPasswordChange}
            />
        </Dialog>
      </Card>

    );
  }
}

WalletList.propTypes = {
  loginActions: PropTypes.object,
  jwtToken: PropTypes.string
};

function mapStateToProps(state) {
  return {
      jwtToken: state.jwtToken
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
)(WalletList);