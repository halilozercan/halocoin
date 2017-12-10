import React, { Component } from 'react';
import MButton from '../components/button.js';
import axios from 'axios';


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
    let default_wallet_name = (this.props.default_wallet === null) ? null:this.props.default_wallet.name;
    if(this.props.wallets !== null) {
      content = this.props.wallets.map((_row, i) => {
                  let isDefault = (_row === default_wallet_name);
                  let defaultButton = '';
                  if(!isDefault){
                    defaultButton = <li><a href="#" onClick={()=>{this.makeDefault(_row);}}>Make Default</a></li>;
                  }

                  return <tr key={i}>
                          <td><h4><b>{_row}</b></h4></td>
                          <td>
                             <div className="dropdown" style={{"float":"right"}}>
                              <button className="btn dropdown-toggle" data-toggle="dropdown">
                                Options
                              </button>
                              <ul className="dropdown-menu">
                                <li><a href="#" onClick={()=>{this.downloadWallet(_row);}}>Backup</a></li>
                                <li><a href="#" onClick={()=>{this.removeWallet(_row);}}>Delete</a></li>
                                {defaultButton}
                              </ul>
                            </div>
                          </td>
                         </tr>;
                });
    }

    return (
      <div className="card">
        <div className="card-header" data-background-color="yellow">
            <h4 className="title">Wallets</h4>
            <p className="category">List of wallets that are managed by halocoin</p>
        </div>
        <div className="card-content table-responsive">
          <table className="table table-hover">
            <tbody>
              {content}
            </tbody>
          </table>
        </div>
      </div>
    );
  }
}

export default WalletList;