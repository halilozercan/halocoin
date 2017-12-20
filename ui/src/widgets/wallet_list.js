import React, { Component } from 'react';
import MButton from '../components/button.js';
import axios from 'axios';
import {List, ListItem} from 'material-ui/List';
import Divider from 'material-ui/Divider';
import {Card, CardActions, CardHeader, CardText} from 'material-ui/Card';
import RaisedButton from 'material-ui/RaisedButton';

class WalletList extends Component {

  constructor(props) {
    super(props);
    this.makeDefault = this.makeDefault.bind(this);
  }

  componentDidMount() {
    this._notificationSystem = this.refs.notificationSystem;
  }

  makeDefault(wallet_name) {
    let password = prompt("Enter Wallet Password", '');
    let data = new FormData();
    data.append('wallet_name', wallet_name);
    data.append('password', password);

    axios.post('/set_default_wallet', data).then((response) => {
      let success = response.data.success;
      if(success) {
        this.props.refresh();
        this.props.notify('Successfully updated your default wallet', 'success');
      }
      else {
        this.props.notify('Failed to update your default wallet', 'error');
      }
    })
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
        this.props.refresh();
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

  render() {
    let content = <div>Loading</div>;
    if(this.props.wallets !== null) {
      content = this.props.wallets.map((_row, i) => {
                    return <ListItem primaryText={_row} />;
                  /*return <tr key={i}>
                          <td><h4><b>{_row}</b></h4></td>
                          <td>
                             <div className="dropdown" style={{"float":"right"}}>
                              <button className="btn dropdown-toggle" data-toggle="dropdown">
                                Options
                              </button>
                              <ul className="dropdown-menu">
                                <li><a href="#" onClick={()=>{this.downloadWallet(_row);}}>Backup</a></li>
                                <li><a href="#" onClick={()=>{this.removeWallet(_row);}}>Delete</a></li>
                                <li><a href="#" onClick={()=>{this.makeDefault(_row);}}>Start</a></li>
                              </ul>
                            </div>
                          </td>
                         </tr>;*/
                });
    }

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
      </Card>
    );
  }
}

export default WalletList;