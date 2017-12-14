import React, { Component } from 'react';
import MAlert from '../components/alert.js';
import axios from 'axios';

class DefaultWallet extends Component {
  constructor(props) {
    super(props);
    this.removeDefault = this.removeDefault.bind(this);
  }

  removeDefault() {
    axios.get('/set_default_wallet?delete').then((response) => {
      this.props.refresh(); 
    })
  }

  render() {
  	let color = "danger";
  	let content = "Not selected!";
    let removeDefaultButton = "";
    if(this.props.wallet !== null) {
      color = "success";
      content = this.props.wallet.name;
      removeDefaultButton = <div style={{float:"right"}}>
                              <button onClick={this.removeDefault} className='btn btn-warning'>Remove Default</button>
                            </div>
    }
    return (
      <div className="col-lg-6 col-md-12 col-sm-12">
        <div className="card">
          <MAlert type={color} icon="explore" text="Default wallets are stored as decrypted. Any action requiring a wallet will be performed with default wallet if another is not given.">
            {removeDefaultButton}
          </MAlert>
          <div className="card-content">
            {this.props.children}
          </div>
        </div>
      </div>
    );
  }
}

export default DefaultWallet;