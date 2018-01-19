import React, { Component } from 'react';
import {List, ListItem} from 'material-ui/List';
import {Card, CardHeader, CardText} from 'material-ui/Card';
import RaisedButton from 'material-ui/RaisedButton';
import Dialog from 'material-ui/Dialog';
import TextField from 'material-ui/TextField';
import axios from 'axios';

class WalletList extends Component {

  constructor(props) {
    super(props);
    this.state = {
      open: false
    }
  }

  removeWallet(wallet_name) {
    let password = prompt("Enter Wallet Password", '');
    let data = new FormData();
    data.append('wallet_name', wallet_name);
    data.append('password', password);

    axios.post('/remove_wallet', data).then((response) => {
      data = response.data;
      if(data.success) {
        this.props.notify(data.message, 'success');
        //this.props.refresh();
      } else {
        this.props.notify(data.error, 'error');
      }
    })
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

  setDefaultWallet = () => {
    let password = this.state.password;
    let data = new FormData();
    data.append('wallet_name', this.state.name);
    data.append('password', password);

    axios.post('/set_default_wallet', data).then((response) => {
      let success = response.data.success;
      if(success) {
        this.props.notify('Successfully updated your default wallet', 'success');
      }
      else {
        this.props.notify('Failed to update your default wallet', 'error');
      }
    })

    this.setState({open: false});
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
        onClick={this.setDefaultWallet}
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

export default WalletList;