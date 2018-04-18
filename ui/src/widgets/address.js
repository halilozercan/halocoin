import React, { Component } from 'react';
import {Card,  CardHeader} from 'material-ui/Card';
import Avatar from 'material-ui/Avatar';
import FontIcon from 'material-ui/FontIcon';
import {red500} from 'material-ui/styles/colors';


class Address extends Component {

  copyToClipboard = () => {
    var textField = document.createElement('textarea');
    textField.innerText = this.props.account.address;
    document.body.appendChild(textField);
    textField.select();
    document.execCommand('copy');
    textField.remove();
    this.props.notify('Address is copied to clipboard', 'info', 'tc');
  }

  render() {
    if(this.props.account !== null) {
      return (
        <Card>
          <CardHeader
            onClick={()=> {
              this.copyToClipboard();
              this.props.notify("Copied to Clipboard!");
            }}
            title="Address"
            subtitle={this.props.account.address}
            avatar={
              <Avatar 
                style={{cursor:"pointer"}} 
                backgroundColor={red500} 
                icon={<FontIcon className="material-icons">adjust</FontIcon>} 
              />
            }
          />
        </Card>
      );
    }
    else {
      return <div />;
    }
  }
}

export default Address;